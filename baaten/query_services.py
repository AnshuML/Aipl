import openai
import re
import numpy as np
from rank_bm25 import BM25Okapi
from services.translation_service import TranslationService
import requests
import time

class QueryProcessor:
    def __init__(self, department_manager):
        self.department_manager = department_manager
        self.translator = TranslationService()

    def process_query(self, query, department, language_code='en', top_k=3):
        # 1. Load department docs (chunks)
        docs = self.department_manager.get_department_docs(department)
        if not docs:
            return "❌ No documents found for this department. Please upload via admin."

        # 2. BM25 retrieval
        bm25 = BM25Okapi([doc.lower().split() for doc in docs])
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)
        bm25_top_idx = np.argsort(bm25_scores)[::-1][:top_k]
        bm25_chunks = [docs[i] for i in bm25_top_idx]

        # 3. Embedding (FAISS) retrieval with error handling
        faiss_index = self.department_manager.get_department_index(department)
        faiss_chunks = []
        if faiss_index is not None:
            try:
                emb = self.department_manager.get_openai_embeddings([query])[0] if hasattr(self.department_manager, 'get_openai_embeddings') else self.department_manager.get_embeddings([query])[0]
                D, I = faiss_index.search(np.array([emb]).astype('float32'), top_k)
                # Filter indices to ensure they're within bounds
                valid_indices = [i for i in I[0] if 0 <= i < len(docs)]
                faiss_chunks = [docs[i] for i in valid_indices]
            except Exception as e:
                print(f"Warning: FAISS embedding search failed: {str(e)}. Using BM25 results only.")
                faiss_chunks = []

        # 4. Merge (deduplicate, preserve order)
        hybrid_chunks = []
        seen = set()
        for chunk in bm25_chunks + faiss_chunks:
            if chunk not in seen:
                hybrid_chunks.append(chunk)
                seen.add(chunk)
        hybrid_context = '\n---\n'.join(hybrid_chunks)

        # 5. LLM prompt with hybrid context, friendly and department-agnostic
        system_prompt = (
            "You are a helpful assistant for company employees. Use the following department documents and FAQs to answer the user's question as accurately, clearly, and in as much detail as possible. "
            "Be friendly, conversational, and helpful. If the answer is not present, say so politely.\n\n"
            f"Relevant content:\n{hybrid_context}\n\n"
            "User question: {user_query}\n"
        )
        
        # Try OpenAI API with retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt.replace('{user_query}', query)},
                        {"role": "user", "content": query}
                    ]
                )
                answer = response['choices'][0]['message']['content']
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"OpenAI API attempt {attempt + 1} failed: {str(e)}. Retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    # Fallback response when OpenAI is unavailable
                    answer = f"❌ Error: Unable to connect to AI service. Please check your internet connection and try again. Error details: {str(e)}"
                    break

        # 6. Translate answer if needed
        if language_code and language_code != 'en':
            try:
                answer = self.translator.translate_text(answer, language_code)
            except Exception as e:
                answer = f"Translation error: {str(e)}"
        return answer