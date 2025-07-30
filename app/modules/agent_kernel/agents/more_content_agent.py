import logging
from typing import Dict, Any, Optional, List
import re
from .base_agent import BaseAgent
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
import asyncio
from ..utils.response_parser import parse_answer_with_embedded_citations

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False

logger = logging.getLogger(__name__)

class MoreContentAgent(BaseAgent):
    """Agent for handling requests for more information on a previous topic from any agent type."""

    def __init__(self, settings):
        super().__init__(settings)
        self.search_endpoint = settings.AZURE_AI_SEARCH_ENDPOINT
        self.search_api_key = settings.AZURE_AI_SEARCH_API_KEY
        self.search_index_name = "ma3refa-pdf-index-v3"
        
        self.excel_file_path = "data/marefa_docs_data.xlsx"
        self._excel_df = None
        self._prompt_manager = None

        if not all([self.search_endpoint, self.search_api_key]):
            raise ValueError("Missing required Azure AI Search settings")

        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.search_index_name,
            credential=AzureKeyCredential(self.search_api_key)
        )

    @property
    def prompt_manager(self):
        """Lazy load PromptManager to avoid circular imports."""
        if self._prompt_manager is None:
            from ...prompt_manager.manager import PromptManager
            self._prompt_manager = PromptManager()
        return self._prompt_manager

    async def _load_excel_data(self):
        """Load Excel data into pandas DataFrame for study queries."""
        try:
            if self._excel_df is None and PANDAS_AVAILABLE:
                def load_excel():
                    return pd.read_excel(self.excel_file_path)
                self._excel_df = await asyncio.to_thread(load_excel)
        except Exception as e:
            logger.error(f"Error loading Excel data: {e}")
            self._excel_df = None

    async def _execute_pandas_query(self, pandas_code: str) -> Any:
        """Execute pandas query safely on Excel data."""
        try:
            def execute_code():
                df = self._excel_df.copy()
                safe_builtins = {
                    'len': len, 'str': str, 'int': int, 'float': float,
                    'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
                    'max': max, 'min': min, 'sum': sum, 'abs': abs, 'round': round,
                }
                local_vars = {"df": df, "pd": pd, "__builtins__": safe_builtins}
                result = eval(pandas_code, {"__builtins__": safe_builtins}, local_vars)
                return result
            
            result = await asyncio.to_thread(execute_code)
            return result
        except Exception as e:
            logger.error(f"Error executing pandas query: {e}")
            return f"Error executing query: {str(e)}"

    async def _generate_pandas_query(self, query: str) -> tuple[str, str]:
        """Generate pandas code and Arabic response using study prompt."""
        try:
            general_prompt = self.prompt_manager.get_prompt("study", "general_query")
            if not general_prompt:
                logger.error("Could not load study general_query prompt")
                return "", ""
            
            formatted_prompt = general_prompt.replace("{{$query}}", query)
            messages = [{"role": "system", "content": formatted_prompt}]
            
            completion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=0.1
            )
            
            ai_response = completion.choices[0].message.content.strip()
            
            pandas_code = ""
            arabic_response = ""
            
            if "PANDAS_CODE:" in ai_response:
                code_start = ai_response.find("PANDAS_CODE:") + 12
                code_end = ai_response.find("ARABIC_RESPONSE:")
                if code_end == -1:
                    code_end = len(ai_response)
                pandas_code = ai_response[code_start:code_end].strip()
            
            if "ARABIC_RESPONSE:" in ai_response:
                response_start = ai_response.find("ARABIC_RESPONSE:") + 16
                arabic_response = ai_response[response_start:].strip()
            
            if pandas_code.startswith("```python"):
                pandas_code = pandas_code[9:]
            if pandas_code.startswith("```"):
                pandas_code = pandas_code[3:]
            if pandas_code.endswith("```"):
                pandas_code = pandas_code[:-3]
            
            pandas_code = pandas_code.strip()
            return pandas_code, arabic_response
            
        except Exception as e:
            logger.error(f"Error generating pandas query: {e}")
            return "", ""

    async def _format_study_response(self, arabic_response: str, result: Any, start_offset: int = 0) -> str:
        """Format study results using the same logic as study agent."""
        try:
            if isinstance(result, pd.DataFrame):
                if len(result) == 0:
                    return f"{arabic_response}\n\nلم يتم العثور على نتائج مطابقة."
                else:
                    count = len(result)
                    display_count = min(20, count)
                    
                    if start_offset == 0:
                        response = f"{arabic_response}\n\nتم العثور على {count:,} دراسة. إليك عينة من أول {display_count} دراسة:\n\n"
                    else:
                        response = f"{arabic_response}\n\n"
                    
                    for i, (idx, row) in enumerate(result.head(display_count).iterrows(), 1):
                        title = row.get('DOCUMENT_TITLE', 'غير متوفر')
                        if pd.isna(title) or title == '':
                            title = row.get('DOCUMENT_TITLE_1', 'غير متوفر')
                        
                        category = row.get('MAIN_CATEGORY_NAME_AR', 'غير محدد')
                        if pd.isna(category):
                            category = 'غير محدد'
                            
                        response += f"{start_offset + i}. العنوان: {title}\n"
                        response += f"   الفئة: {category}\n\n"
                    
                    if count > display_count and start_offset == 0:
                        response += f"\n... و {count - display_count:,} دراسة أخرى.\n\n"
                        response += f"💡 اكتب 'المزيد' لعرض المزيد من النتائج."
                    
                    return response
            elif isinstance(result, (int, float)):
                return f"{arabic_response}\n\n{result:,}"
            else:
                return f"{arabic_response}\n\n{str(result)}"
        except Exception as e:
            logger.error(f"Error formatting study response: {e}")
            return f"{arabic_response}\n\nالنتيجة: {result}"

    async def _generate_query_embedding(self, query: str) -> List[float]:
        try:
            logger.info(f"Generating embeddings for query: {query[:100]}...")
            response = self.client.embeddings.create(input=query, model="text-embedding-ada-002")
            embedding = response.data[0].embedding
            logger.info(f"Generated embedding vector of length: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            return []

    async def _search(self, query: str, top: int = 5, skip: int = 0) -> List[Dict[str, Any]]:
        select_fields = [
            "id", "content", "document_category", "chunk_category", 
            "page_number", "chunk_number", "document_title", "dms_doc_id", 
            "file_name", "category_name", "document_id", "main_category_name_ar", 
            "classification_name_ar", "document_status_ar", "document_classification_id", 
            "main_category_id", "entities_entity_id", "document_version", 
            "document_date", "document_title_1", "document_views_count", 
            "document_publish_date", "document_creation_date", "updated_date", 
            "document_description", "document_lang", "eversuite_url", "dmsdocid_1"
        ]
        
        try:
            query_embedding = await self._generate_query_embedding(query)
            if query_embedding:
                logger.info(f"Performing hybrid search (text + semantic) with skip={skip}")
                vector_query = VectorizedQuery(vector=query_embedding, k_nearest_neighbors=top, fields="embedding")
                search_results = self.search_client.search(
                    search_text=query,
                    vector_queries=[vector_query],   
                    select=select_fields,
                    top=top,
                    skip=skip
                )
            else:
                logger.warning(f"Failed to generate embeddings, falling back to text-only search with skip={skip}")
                search_results = self.search_client.search(
                    search_text=query, select=select_fields, top=top, skip=skip
                )
            
            results_list = [dict(result) for result in search_results]
            logger.info(f"Retrieved {len(results_list)} results from paginated search")
            return results_list
        except Exception as e:
            logger.error(f"Error in paginated search: {str(e)}")
            return []

    async def execute(self, query: str, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if not context:
            return {"response": {"content": "I don't have any previous conversation to get more content from."}, "status": "error"}

        last_agent_message = None
        previous_agent_type = None
        
        for msg in reversed(context):
            message_data = msg.get("message_data", {})
            if message_data.get("type") == "agent_response":
                response_data = message_data.get("response", {})
                if isinstance(response_data, dict):
                    response_meta = response_data.get("metadata", {})
                else:
                    response_meta = {}
                
                if not response_meta:
                    response_meta = message_data.get("metadata", {})
                
                if response_meta and response_meta.get("agent_type") in ["knowledge_qa", "more_content", "study"]:
                    last_agent_message = message_data
                    previous_agent_type = response_meta.get("agent_type")
                    break
        
        if not last_agent_message:
            return {"response": {"content": "I couldn't find a previous topic to expand on. Could you please ask your original question again?"}, "status": "error"}

        response_data = last_agent_message.get("response", {})
        if isinstance(response_data, dict) and "metadata" in response_data:
            metadata = response_data["metadata"]
        else:
            metadata = last_agent_message.get("metadata", {})
        
        if previous_agent_type == "study":
            return await self._handle_study_more_request(query, metadata, context)
        elif previous_agent_type == "more_content":
            original_agent_type = metadata.get("original_agent_type")
            if original_agent_type == "study" or metadata.get("pandas_code"):
                return await self._handle_study_more_request(query, metadata, context)
            else:
                return await self._handle_knowledge_more_request(query, prompt, metadata)
        else:
            return await self._handle_knowledge_more_request(query, prompt, metadata)

    async def _handle_study_more_request(self, query: str, metadata: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Handle more requests for study agent responses."""
        try:
            if not PANDAS_AVAILABLE:
                return {"response": {"content": "Pandas is required for study data analysis. Please install pandas."}, "status": "error"}
            
            await self._load_excel_data()
            if self._excel_df is None:
                return {"response": {"content": "Could not load study data."}, "status": "error"}

            last_query = metadata.get("last_query")
            pandas_code = metadata.get("pandas_code") 
            total_results = metadata.get("total_results")
            
            if not last_query:
                return {"response": {"content": "I couldn't determine the original study topic. Please ask your question again."}, "status": "error"}

            shown_count = 0
            for msg in reversed(context):
                message_data = msg.get("message_data", {})
                if message_data.get("type") == "agent_response":
                    response_data = message_data.get("response", {})
                    if isinstance(response_data, dict) and "metadata" in response_data:
                        msg_metadata = response_data["metadata"]
                    else:
                        msg_metadata = message_data.get("metadata", {})
                    
                    if msg_metadata and msg_metadata.get("agent_type") in ["study", "more_content"]:
                        if msg_metadata.get("shown_so_far"):
                            shown_count = msg_metadata["shown_so_far"]
                            break
                        if isinstance(response_data, dict) and "content" in response_data:
                            content = response_data.get("content", "")
                        else:
                            content = message_data.get("content", "")
                        
                        if "إليك عينة من أول" in content:
                            import re
                            match = re.search(r'أول (\d+)', content)
                            if match:
                                shown_count = int(match.group(1))
                                break

            if pandas_code and total_results and total_results > shown_count:
                result = await self._execute_pandas_query(pandas_code)
                
                if isinstance(result, pd.DataFrame) and len(result) > shown_count:
                    start_idx = shown_count
                    end_idx = min(start_idx + 20, len(result))
                    next_batch = result.iloc[start_idx:end_idx]
                    
                    arabic_response = f"المزيد من الدراسات (من {start_idx + 1} إلى {end_idx}):"
                    formatted_response = await self._format_study_response(arabic_response, next_batch, start_offset=start_idx)
                    
                    remaining = len(result) - end_idx
                    if remaining > 0:
                        formatted_response += f"\n\n💡 يوجد {remaining} دراسة أخرى. اكتب 'المزيد' لعرض المزيد من النتائج."
                    
                    return {
                        "response": {
                            "content": formatted_response,
                            "metadata": {
                                "agent_type": self.agent_type,
                                "original_agent_type": "study",
                                "last_query": last_query,
                                "pandas_code": pandas_code,
                                "total_results": len(result),
                                "shown_so_far": end_idx
                            }
                        },
                        "agent_type": self.agent_type,
                        "status": "success"
                    }
                else:
                    return {"response": {"content": "لا توجد المزيد من النتائج لعرضها."}, "status": "success"}
            
            pandas_code, arabic_response = await self._generate_pandas_query(last_query)
            if not pandas_code:
                return {"response": {"content": "لم أتمكن من معالجة الاستعلام السابق."}, "status": "error"}
            
            result = await self._execute_pandas_query(pandas_code)
            formatted_response = await self._format_study_response(arabic_response, result, start_offset=shown_count)
            
            return {
                "response": {
                    "content": formatted_response,
                    "metadata": {
                        "agent_type": self.agent_type,
                        "original_agent_type": "study",
                        "last_query": last_query,
                        "pandas_code": pandas_code,
                        "total_results": len(result) if isinstance(result, pd.DataFrame) else None,
                        "shown_so_far": min(shown_count + 20, len(result)) if isinstance(result, pd.DataFrame) else None
                    }
                },
                "agent_type": self.agent_type,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error handling study more request: {e}")
            return {"response": {"content": f"حدث خطأ أثناء معالجة طلب المزيد من النتائج: {str(e)}"}, "status": "error"}

    async def _handle_knowledge_more_request(self, query: str, prompt: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle more requests for knowledge_qa agent responses (original logic)."""
        original_query = metadata.get("original_query")
        
        previous_skip = metadata.get("skip", 0)
        previous_top = metadata.get("top", 5)
        new_skip = previous_skip + previous_top
        
        if not original_query:
            return {"response": {"content": "I'm sorry, I couldn't determine the original topic. Please ask your question again."}, "status": "error"}

        logger.info(f"MoreContentAgent: Found original query '{original_query}'. Fetching next results with skip={new_skip}.")
        search_results = await self._search(original_query, top=5, skip=new_skip)

        is_arabic = any('\u0600' <= char <= '\u06FF' for char in original_query)
        response_language = "Arabic" if is_arabic else "English"

        if not search_results:
            no_more_info_response = "I couldn't find any more information on this topic."
            if is_arabic:
                no_more_info_response = "عذراً، لم أتمكن من العثور على مزيد من المعلومات حول هذا الموضوع."
            return {"response": {"content": no_more_info_response, 
                                 "metadata": {"agent_type": self.agent_type, "original_agent_type": "knowledge_qa", "original_query": original_query, "skip": new_skip, "top": 5}},
                    "status": "success"}

        context_map = {}
        context_for_llm = []
        for i, result in enumerate(search_results):
            doc_id = f"[doc_{i+1}]"
            context_map[doc_id] = {
                "dmsdocid_1": result.get("dmsdocid_1"),
                "document_title": result.get("document_title"),
                "page_number": result.get("page_number")
            }
            context_for_llm.append(
                f"Document ID: {doc_id}\\n"
                f"Title: {result.get('document_title', 'No title')}\\n"
                f"Page: {result.get('page_number', 'N/A')}\\n"
                f"Content: {result.get('content', 'No content')}"
            )

        search_results_content = '\\n\\n---\\n\\n'.join(context_for_llm)
        
        final_system_prompt = prompt.format(
            question=original_query,
            context=search_results_content,
            language=response_language
        )
        
        messages = [{"role": "system", "content": final_system_prompt}, {"role": "user", "content": original_query}]
        llm_response = await self._process_query(messages)
        answer, used_source_ids, related_questions = parse_answer_with_embedded_citations(llm_response)

        # Intelligent Fallback: If primary parsing fails, try to find in-text citations.
        if not used_source_ids and "حسب وثيقة" in answer:
            logger.warning("Standard parsing failed to find source IDs. Falling back to regex on answer text.")
            
            # Extract titles from citations like "**حسب وثيقة 'TITLE'..."
            title_pattern = re.compile(r"\\*\\*حسب وثيقة '([^']+)'")
            found_titles = set(title_pattern.findall(answer))
            
            if found_titles:
                # Rebuild the source IDs by matching titles from the context map.
                title_to_docid_map = {v['document_title']: k for k, v in context_map.items()}
                used_source_ids = [title_to_docid_map[title] for title in found_titles if title in title_to_docid_map]
                logger.info(f"Fallback parser found {len(used_source_ids)} sources from in-text citations.")

        # Final Verification: If we have a non-generic answer but no verified sources, it's a hallucination.
        is_generic_response = any(phrase in answer for phrase in ["لا أملك معلومات كافية", "I do not have enough information", "للأسف"])
        if answer and not used_source_ids and not is_generic_response:
            logger.warning("Agent provided a non-generic answer but no sources could be verified. Clearing sources to prevent misinformation.")
            used_source_ids = []
 
        # Build the final list of documents from the verified source IDs.
        resources_documents = [context_map[doc_id] for doc_id in used_source_ids if doc_id in context_map]

        return {
            "response": {
                "content": answer, 
                "metadata": {
                    "agent_type": self.agent_type,
                    "original_agent_type": "knowledge_qa",
                    "original_query": original_query,
                    "related_questions": related_questions,
                    "resources_documents": resources_documents,
                    "skip": new_skip,
                    "top": 5
                }
            },
            "status": "success"
        }

    async def _process_query(self, messages: list) -> str:
        completion = self.client.chat.completions.create(model=self.deployment_name, messages=messages)
        response = completion.choices[0].message.content
        logger.info(f"Received response from OpenAI: {response[:100]}...")
        return response

    @property
    def agent_type(self) -> str:
        return "more_content" 