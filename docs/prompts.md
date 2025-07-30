# Prompt Management

## Overview

The prompt management system in Maarefa Agent V2 provides a structured way to handle different types of prompts for various agents and use cases.

## Prompt Structure

Prompts are stored in `.prompty` files within the `app/modules/prompt_manager/prompts` directory, organized by agent type:

```
prompts/
├── chat/
│   ├── general.prompty
│   ├── technical.prompty
│   └── creative.prompty
├── summarization/
│   ├── text.prompty
│   ├── document.prompty
│   └── meeting.prompty
├── study/
│   ├── concept.prompty
│   ├── problem.prompty
│   ├── review.prompty
│   └── overview.prompty
├── knowledge_qa/
│   ├── simple_qa.prompty
│   └── complex_qa.prompty
└── clarification/
    ├── general.prompty
    ├── technical.prompty
    └── study.prompty
```

## Prompt Types

### Chat Prompts

1. **General Chat**
   - Purpose: General conversation and interaction
   - Use cases: Casual chat, information requests
   - Key features: Friendly tone, clear responses

2. **Technical Chat**
   - Purpose: Technical discussions and explanations
   - Use cases: Technical queries, concept explanations
   - Key features: Technical accuracy, step-by-step explanations

3. **Creative Chat**
   - Purpose: Creative and imaginative interactions
   - Use cases: Brainstorming, idea generation
   - Key features: Creative thinking, open-ended responses

### Summarization Prompts

1. **Text Summarization**
   - Purpose: Summarize general text content
   - Use cases: Article summaries, content condensation
   - Key features: Main points extraction, concise output

2. **Document Summarization**
   - Purpose: Summarize structured documents
   - Use cases: Report summaries, document overviews
   - Key features: Structure preservation, key information extraction

3. **Meeting Summarization**
   - Purpose: Summarize meeting content
   - Use cases: Meeting notes, action items
   - Key features: Action item extraction, decision tracking

### Study Prompts

1. **Concept**
   - Purpose: Explain study concepts
   - Use cases: Concept understanding, topic explanation
   - Key features: Clear explanations, examples

2. **Problem**
   - Purpose: Handle study-related problems
   - Use cases: Problem solving, exercise guidance
   - Key features: Step-by-step solutions, explanations

3. **Review**
   - Purpose: Review study materials
   - Use cases: Material review, knowledge check
   - Key features: Comprehensive coverage, key points

4. **Overview**
   - Purpose: Provide study overviews
   - Use cases: Course overview, topic introduction
   - Key features: Structure presentation, key concepts

### Knowledge QA Prompts

1. **Simple QA**
   - Purpose: Handle straightforward questions
   - Use cases: Factual queries, direct answers
   - Key features: Concise responses, accuracy

2. **Complex QA**
   - Purpose: Handle complex questions
   - Use cases: Detailed explanations, multi-part answers
   - Key features: Comprehensive responses, context

### Clarification Prompts

1. **General Clarification**
   - Purpose: General query refinement
   - Use cases: Query clarification, understanding improvement
   - Key features: Clear questions, helpful suggestions

2. **Technical Clarification**
   - Purpose: Technical concept clarification
   - Use cases: Technical term explanation, concept understanding
   - Key features: Technical accuracy, step-by-step explanation

3. **Study Clarification**
   - Purpose: Study-related clarification
   - Use cases: Study concept clarification, methodology explanation
   - Key features: Learning-focused, example-based

## Prompt Guidelines

1. **Structure**
   - Clear role definition
   - Specific guidelines
   - Example responses
   - Error handling

2. **Content**
   - Clear and concise
   - Context-aware
   - Purpose-specific
   - User-friendly

3. **Format**
   - Consistent structure
   - Markdown support
   - Clear sections
   - Easy to maintain

## Best Practices

1. **Writing Prompts**
   - Be specific and clear
   - Include examples
   - Define boundaries
   - Consider edge cases

2. **Maintaining Prompts**
   - Regular updates
   - Version control
   - Documentation
   - Testing

3. **Using Prompts**
   - Context awareness
   - Dynamic selection
   - Error handling
   - Performance optimization

## Adding New Prompts

1. Create a new prompt file:
```prompty
# Role and Purpose
You are a [role]. Your purpose is to [purpose].

# Guidelines
- Guideline 1
- Guideline 2
- Guideline 3

# Examples
Example 1: [example]
Example 2: [example]

# Error Handling
- Handle case 1 by [action]
- Handle case 2 by [action]
```

2. Register the prompt type in the agent registry:
```python
_agent_prompt_types: Dict[str, List[str]] = {
    "agent_type": ["existing_type", "new_type"]
}
```

## Testing Prompts

1. **Unit Testing**
   - Test prompt loading
   - Verify structure
   - Check content

2. **Integration Testing**
   - Test with agents
   - Verify responses
   - Check performance

3. **User Testing**
   - Gather feedback
   - Measure effectiveness
   - Identify improvements 