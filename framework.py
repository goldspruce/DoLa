import os
import math
from openai import OpenAI

# Initialize OpenAI Client (Ensure your OPENAI_API_KEY is set in your environment)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_classification_logprob(prompt: str, persona_system_prompt: str, target_token: str, model="gpt-4o-mini"):
    """
    Calls the LLM with a specific persona and retrieves the log probability of the target token.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": persona_system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1, # We only want the classification token
        logprobs=True,
        top_logprobs=5,
        temperature=0.0
    )
    
    # Extract the logprobs from the first token of the response
    logprobs_list = response.choices[0].logprobs.content[0].top_logprobs
    
    # Search for our target token's logprob
    target_logprob = None
    for lp in logprobs_list:
        if lp.token.strip().lower() == target_token.lower():
            target_logprob = lp.logprob
            break
            
    # If the token wasn't in the top 5, assign a heavily penalized logprob
    if target_logprob is None:
        target_logprob = -10.0 
        
    # Convert logprob to actual probability for display purposes
    probability = math.exp(target_logprob)
    
    return target_logprob, probability

def dola_classifier(input_text: str, candidate_label: str):
    """
    Runs the 'Council of Minds' DoLa SP Algorithm.
    """
    # 1. Define the Personas based on the AICRAFT text
    naive_prompt = "You are a naive guesser. Rely on your first instinct and superficial surface-level associations. Classify the following text with a single word." # [cite: 151]
    expert_prompt = "You are a careful reasoner. Analyze the deep logic, intent, context, and subtle nuances of the text. Classify the following text with a single word." # [cite: 153]

    user_prompt = f"Text: '{input_text}'\nIs the core sentiment or intent here '{candidate_label}'? Answer only with 'Yes' or 'No'."
    target_token = "Yes"

    print(f"\n--- Analyzing: '{input_text}' for label '{candidate_label}' ---")

    # 2. Get Naive (Early Layer Analogue) Logprobs
    naive_logprob, naive_prob = get_classification_logprob(user_prompt, naive_prompt, target_token)
    
    # 3. Get Expert (Late Layer Analogue) Logprobs
    expert_logprob, expert_prob = get_classification_logprob(user_prompt, expert_prompt, target_token)

    # 4. Calculate DoLa Score (Expert - Naive)
    dola_score = expert_logprob - naive_logprob

    # 5. Output Results formatting matching the DoLa Classifier Table
    print(f"Naive State (Reflex): {naive_prob*100:.2f}% (Logprob: {naive_logprob:.2f})")
    print(f"Expert State (Reason): {expert_prob*100:.2f}% (Logprob: {expert_logprob:.2f})")
    print(f"DoLa Score (Logit Diff): {dola_score:.2f}")
    
    if dola_score > 0:
        print("Interpretation: GAIN (True Signal / Hidden Truth) - The expert actively promoted this.") # [cite: 233, 246]
    else:
        print("Interpretation: LOSS (Suppressed Bias) - The expert actively suppressed this initial reflex.") # [cite: 233, 246]

# --- Run the tests from the document ---
if __name__ == "__main__":
    # Test 1: The Sarcastic/Figurative Idiom
    dola_classifier("I'm dying to meet you!", "Emergency") # [cite: 233, 246]
    dola_classifier("I'm dying to meet you!", "Excitement") # [cite: 233, 246]

    # Test 2: The Contextual Shift
    dola_classifier("The bank is completely flooded.", "Financial Institution") # [cite: 246]
    dola_classifier("The bank is completely flooded.", "River Bank") # [cite: 246]
