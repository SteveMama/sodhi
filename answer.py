import os
import PyPDF2
from transformers import AutoTokenizer, AutoModel
import torch
import chromadb
from groq import Groq


client = Groq(api_key="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")

# Load the embedding model
embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
tokenizer = AutoTokenizer.from_pretrained(embedding_model_name)
model = AutoModel.from_pretrained(embedding_model_name).to('cpu')

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="vectordb")
collection = chroma_client.get_collection("all_pdfs")

def encode_question(question):
    """Convert a question into an embedding."""
    inputs = tokenizer(question, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        embedding = outputs.last_hidden_state[:, 0, :]
    return embedding.cpu().numpy().tolist()[0]

def search_similar_chunks(question_embedding, top_k=20):
    """Search for the top k similar chunks in the ChromaDB collection."""
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k
    )
    return list(zip(results['documents'][0], results['metadatas'][0], results['distances'][0]))

def answer_question(question):
    try:
        # Encode the question
        question_embedding = encode_question(question)

        # Search for similar chunks
        similar_chunks = search_similar_chunks(question_embedding)

        # Retrieve the content of the top chunks
        context = ""
        for chunk_content, metadata, distance in similar_chunks:
            context += f"From {metadata['source']}, chunk {metadata['chunk_id']}:\n{chunk_content}\n\n"

        print("Context retrieved successfully.")  # Debug print

        # Prepare the prompt for the LLM
        prompt = f"""Context information is below.
        ---------------------
        {context}
        ---------------------
        Given the context information and not prior knowledge, answer the question: {question}
        """

        print(prompt)

        # Use Groq API to get the answer
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions based on the given context. If you don't find relevant information, reply with 'I do not have information'.",
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-8b-8192",
            temperature=0.5,
            max_tokens=500,
        )

        print("API call completed successfully.")  # Debug print

        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"An error occurred: {str(e)}")  # Print the error message
        return f"An error occurred: {str(e)}"

print("Starting the question-answering process...")  # Debug print

# Example usage
user_question = "clean energy"
answer = answer_question(user_question)
print(f"Question: {user_question}")
print(f"Answer: {answer}")

print("Process completed.")  # Debug print
