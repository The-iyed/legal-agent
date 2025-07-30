from typing import Dict, Any, Optional, List
import asyncio
from .base_agent import BaseAgent
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType, QueryCaptionType, QueryAnswerType
import logging
from ..utils.response_parser import parse_answer_with_embedded_citations
import re

logger = logging.getLogger(__name__)


class KnowledgeQAAgent(BaseAgent):

    def __init__(self, settings):
        super().__init__(settings)
        self.search_endpoint = settings.AZURE_AI_SEARCH_ENDPOINT
        self.search_api_key = settings.AZURE_AI_SEARCH_API_KEY
        self.search_index_name = "tachriat-documents"

        if not all([self.search_endpoint, self.search_api_key]):
            raise ValueError("Missing required Azure AI Search settings")

        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.search_index_name,
            credential=AzureKeyCredential(self.search_api_key)
        )

    def _clean_document_title(self, title: str) -> str:
        """Clean document title by removing ID prefix pattern like '4200574671 - '"""
        if not title:
            return title
        
        # Remove patterns like "4200574671 - " from the beginning of the title
        cleaned_title = re.sub(r'^\d+\s*-\s*', '', title.strip())
        return cleaned_title

    async def _generate_query_embedding(self, query: str) -> List[float]:
        try:
            logger.info(f"Generating embeddings for query: {query[:100]}...")
            
            response = self.client.embeddings.create(
                input=query,
                model="text-embedding-ada-002"
            )
            
            embedding = response.data[0].embedding
            logger.info(f"Generated embedding vector of length: {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            return []

    async def _search(self, query: str, top: int = 5, skip: int = 0) -> List[Dict[str, Any]]:
        select_fields = [
            "attachment_id", "document_name", "content", "content_en", "chunk_id", 
            "page_number", "legislation_title", "legislation_number", "legislation_type", 
            "legislation_date", "legislation_subject", "issuing_authority", "legal_status",
            "pillar_name", "authority", "classification_name", "file_name"
        ]

        def do_semantic_search(search_query: str):
            """Executes semantic search with semantic_engine configuration."""
            return self.search_client.search(
                search_query,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="my-semantic-config",
                query_caption=QueryCaptionType.EXTRACTIVE,
                query_answer=QueryAnswerType.EXTRACTIVE,
                select=select_fields,
                top=top,
                skip=skip
            )

        loop = asyncio.get_running_loop()
        
        try:
            logger.info(f"Performing semantic search for query: '{query}' (top: {top}, skip: {skip})")
            
            semantic_results = await loop.run_in_executor(None, do_semantic_search, query)
            semantic_list = [dict(result) for result in semantic_results]
            logger.info(f"Semantic search returned {len(semantic_list)} results")
            
            if semantic_list:
                for i, result in enumerate(semantic_list[:3]): 
                    raw_title = result.get('document_name') or result.get('legislation_title', 'No title')
                    clean_title = self._clean_document_title(raw_title)
                    content_preview = result.get('content', '')[:100] + '...' if result.get('content') else 'No content'
                    logger.info(f"  Result {i+1}: {clean_title} - {content_preview}")
            
            return semantic_list
            
        except Exception as e:
            logger.error(f"Error during semantic search: {str(e)}")
            return []

    async def execute(self, query: str, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        try:
            is_arabic = any('\u0600' <= char <= '\u06FF' for char in query)
            response_language = "Arabic" if is_arabic else "English"

            logger.info(f"KnowledgeQAAgent: Searching for query: {query[:100]}...")
            search_results = await self._search(query, top=7)
            
            logger.info(f"In execute method - search_results type: {type(search_results)}")
            logger.info(f"In execute method - search_results value: {search_results}")
            logger.info(f"In execute method - bool(search_results): {bool(search_results)}")
            logger.info(f"In execute method - len(search_results): {len(search_results) if search_results else 'None/Empty'}")
            
            if not search_results:
                 logger.warning(f"No search results found for query: {query}")
                 no_info_response = "للأسف، لم يتم العثور على معلومات ذات صلة في مكتبة التشريعات للإجابة على سؤالك." if is_arabic else "Unfortunately, no relevant information was found in the legislative library."
                 return {"response": {"content": no_info_response, "metadata": {"original_query": query}}, "status": "success"}

            logger.info(f"Retrieved {len(search_results)} documents for query: {query}")
            for i, result in enumerate(search_results):
                content_preview = result.get('content', '')[:100] + '...' if result.get('content') else 'No content'
                raw_title = result.get('document_name') or result.get('legislation_title', 'No title')
                clean_title = self._clean_document_title(raw_title)
                logger.info(f"Document {i+1}: Title='{clean_title}', Content preview: {content_preview}")

            context_map = {}
            context_for_llm = []
            for i, result in enumerate(search_results):
                doc_id = f"[doc_{i+1}]"
                legislation_date = result.get("legislation_date", "N/A")
                if legislation_date and ' ' in legislation_date:
                    legislation_date = legislation_date.split(' ')[0]

                # Clean the titles before storing in context_map
                raw_document_name = result.get("document_name", "")
                raw_legislation_title = result.get("legislation_title", "")
                clean_document_name = self._clean_document_title(raw_document_name) if raw_document_name else ""
                clean_legislation_title = self._clean_document_title(raw_legislation_title) if raw_legislation_title else ""

                context_map[doc_id] = {
                    "dmsdocid_1": result.get("attachment_id"),  # Use attachment_id value for dmsdocid_1
                    "document_title": clean_legislation_title or clean_document_name,  # Use legislation_title value for document_title
                    "document_name": clean_document_name,
                    "legislation_title": clean_legislation_title,
                    "legislation_number": result.get("legislation_number"),
                    "legislation_type": result.get("legislation_type"),
                    "page_number": result.get("page_number"),
                    "issuing_authority": result.get("issuing_authority"),
                    "legal_status": result.get("legal_status")
                }
                
                content = result.get('content', 'No content available')
                title = clean_document_name or clean_legislation_title or 'No title'
                legislation_number = result.get('legislation_number', 'N/A')
                legislation_type = result.get('legislation_type', 'N/A')
                issuing_authority = result.get('issuing_authority', 'N/A')
                legal_status = result.get('legal_status', 'N/A')
                legislation_subject = result.get('legislation_subject', 'N/A')
                pillar_name = result.get('pillar_name', 'N/A')
                classification_name = result.get('classification_name', 'N/A')
                
                context_for_llm.append(
                    f"Document ID: {doc_id}\n"
                    f"Title: {title}\n"
                    f"Legislation Number: {legislation_number}\n"
                    f"Legislation Type: {legislation_type}\n"
                    f"Date: {legislation_date}\n"
                    f"Issuing Authority: {issuing_authority}\n"
                    f"Legal Status: {legal_status}\n"
                    f"Legislation Subject: {legislation_subject}\n"
                    f"Pillar Name: {pillar_name}\n"
                    f"Classification: {classification_name}\n"
                    f"Page: {result.get('page_number', 'N/A')}\n"
                    f"Content: {content}\n"
                    f"---"
                )

            search_results_content = '\n\n'.join(context_for_llm)
            
            logger.info(f"Context length for LLM: {len(search_results_content)} characters")
            logger.info(f"Context preview: {search_results_content[:500]}...")
            
            system_prompt = prompt.format(
                question=query, 
                context=search_results_content, 
                language=response_language
            )
            
            logger.info(f"System prompt length: {len(system_prompt)} characters")
            logger.info(f"System prompt preview: {system_prompt[:1000]}...")
            
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": query}]

            llm_response = await self._process_query(messages)
            
            answer, used_source_ids, related_questions = parse_answer_with_embedded_citations(llm_response)

            is_generic_response = any(phrase in answer for phrase in ["لا أملك معلومات كافية", "I do not have enough information", "ليس لدي معلومات كافية"])
            
            if answer and not used_source_ids and not is_generic_response:
                logger.warning(f"Hallucination detected for query '{query[:100]}...'. Overriding response.")
                related_questions = []
                used_source_ids = []

            resources_documents = []
            for doc_id in used_source_ids:
                if doc_id in context_map:
                    resources_documents.append(context_map[doc_id])

            return {
                "response": {"content": answer, "metadata": {
                    "agent_type": self.agent_type,
                    "original_query": query,
                    "related_questions": related_questions,
                    "resources_documents": resources_documents
                    }},
                "agent_type": self.agent_type,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error in KnowledgeQAAgent execution: {str(e)}", exc_info=True)
            return {"error": str(e), "status": "error"}

    async def _process_query(self, messages: Optional[List[Dict[str, str]]] = None) -> str:
        if not messages:
            return "No messages to process."

        completion = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages
        )
        
        response = completion.choices[0].message.content
        logger.info(f"Received response from OpenAI: {response[:100]}...")
        return response
    
    @property
    def agent_type(self) -> str:
        return "knowledge_qa" 
