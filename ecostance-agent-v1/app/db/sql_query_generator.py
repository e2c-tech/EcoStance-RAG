import google.genai as genai
import os
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

class SQLQueryGenerator:
    """
    Generates SQL queries from natural language questions using an LLM.
    """
    def __init__(self, schema, model=None):
        """
        Initializes the SQLQueryGenerator.
        """
        self.schema = schema
        self.provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        
        # Determine model and provider
        if not model:
            model = os.getenv("AGENT_MODEL")
            
        if self.provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY must be set when LLM_PROVIDER is 'groq'")
            
            # Default Groq model if not provided
            if not model or "gemini" in model.lower():
                model = "llama-3.3-70b-versatile"
                
            self.llm = ChatGroq(
                model=model,
                groq_api_key=api_key,
                temperature=0.1
            )
            self.model_name = model
            logger.info(f"SQLQueryGenerator initialized with Groq model: {model}")
        else:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY must be set in environment variables")
            
            # Default Gemini model if not provided
            if not model or "llama" in model.lower():
                model = "gemini-1.5-flash"
                
            self.llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=0.1
            )
            self.model_name = model
            logger.info(f"SQLQueryGenerator initialized with Gemini model: {model}")

    async def generate_query(self, user_question):
        """
        Generates a SQL query from a user's natural language question.
        """
        prompt = self._create_prompt(user_question)
        
        try:
            # Use LangChain LLM for provider abstraction
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            generated_text = response.content.strip()
            
            sql_query = self._extract_sql_from_response(generated_text)
            explanation = self._extract_explanation(generated_text)
            safety_check = self._assess_safety(sql_query)

            return {
                "sql_query": sql_query,
                "explanation": explanation,
                "safety_check": safety_check
            }
        except Exception as e:
            logger.error(f"SQL Generation Error: {str(e)}")
            # If Gemini failed with 403 (leaked), and we have a Groq alternative, we could potentially retry here.
            # But for now, let's just surface the error or fix the initialization.
            return {"error": f"Failed to generate SQL query: {str(e)}"}

    def _create_prompt(self, user_question):
        """
        Creates the prompt for the language model.
        """
        schema_representation = self._format_schema()
        prompt = f"""
        Given the following database schema:
        {schema_representation}

        Generate a SQL query that answers the following question:
        "{user_question}"

        The query must be safe and read-only (only SELECT statements).
        Do not include any write operations like INSERT, UPDATE, or DELETE.
        Also, provide a brief explanation of what the query does.
        
        Return the response in a structured format with the SQL query inside a ```sql code block
        and the explanation in a separate section.
        """
        return prompt

    def _format_schema(self):
        """
        Formats the schema into a string representation for the prompt.
        """
        schema_str = ""
        # Handle SQL schema
        if 'tables' in self.schema:
            for table_name, details in self.schema['tables'].items():
                schema_str += f"Table '{table_name}':\n"
                for col in details['columns']:
                    pk = " (PK)" if col['name'] in details.get('primary_keys', []) else ""
                    schema_str += f"  - {col['name']} ({col['type']}){pk}\n"
                
                if details.get('foreign_keys'):
                    schema_str += "  Foreign Keys:\n"
                    for fk in details['foreign_keys']:
                        schema_str += f"    - {fk['constrained_columns']} -> {fk['referred_table']}({fk['referred_columns']})\n"
                schema_str += "\n"
        
        # Handle MongoDB schema
        if 'collections' in self.schema:
            for col_name, details in self.schema['collections'].items():
                schema_str += f"Collection '{col_name}':\n"
                for field, f_type in details.get('fields', {}).items():
                    schema_str += f"  - {field} ({f_type})\n"
                schema_str += "\n"

        return schema_str

    def _extract_sql_from_response(self, response_text):
        """
        Extracts the SQL query from the model's response.
        """
        try:
            # Find the SQL block and extract it
            sql_part = response_text.split("```sql")[1]
            return sql_part.split("```")[0].strip()
        except IndexError:
            # Fallback for when the model doesn't use the code block
            return response_text.strip()

    def _extract_explanation(self, response_text):
        """
        Extracts the explanation from the model's response.
        """
        if "Explanation:" in response_text:
            try:
                return response_text.split("Explanation:")[1].strip().split("```")[0]
            except IndexError:
                return "No explanation provided."
        return "No explanation provided."

    def _assess_safety(self, sql_query):
        """
        Performs a basic safety check on the generated SQL query.
        """
        # Simple check for read-only queries
        if sql_query.strip().upper().startswith("SELECT"):
            return "SAFE"
        return "UNSAFE"
