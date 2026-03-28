import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

def true_dola_classifier(
    prompt: str, 
    target_token_str: str, 
    model_name: str = "gpt2", 
    early_layer_idx: int = 2
):
    """
    Implements true Decoding by Contrasting Layers (DoLa).
    Subtracts early-layer logits (reflex/bias) from late-layer logits (context/reasoning).
    
    Args:
        prompt (str): The input text to analyze.
        target_token_str (str): The token we are scoring (e.g., "Yes", "Positive").
        model_name (str): HuggingFace model ID. (Using 'gpt2' for accessibility, but 
                          works best on modern models like 'meta-llama/Llama-2-7b-hf').
        early_layer_idx (int): The index of the layer to treat as the "naive reflex".
    """
    print(f"Loading {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, output_hidden_states=True)
    model.eval() # Set to evaluation mode

    # 1. Prepare Inputs
    inputs = tokenizer(prompt, return_tensors="pt")
    
    # Ensure the target token is a single token in the model's vocabulary
    target_token_id = tokenizer.encode(target_token_str)[0]

    with torch.no_grad():
        # 2. Forward pass, extracting hidden states from ALL layers
        outputs = model(**inputs)
        
        # 'hidden_states' is a tuple of (embedding_output, layer_1, layer_2, ..., final_layer)
        hidden_states = outputs.hidden_states
        
        # 3. Extract the Early Layer (The "Naive Reflex" / Egocentric State)
        # We take the state from the specified early layer, looking at the LAST token in the prompt
        early_hidden_state = hidden_states[early_layer_idx][0, -1, :]
        
        # 4. Extract the Late Layer (The "Expert Reasoning" / Theory of Mind State)
        # We take the final transformer layer (index -1)
        late_hidden_state = hidden_states[-1][0, -1, :]

        # 5. Project hidden states into Vocabulary Logits
        # Models use an 'lm_head' (Language Modeling Head) to map hidden states back to words
        # Note: Depending on the architecture, you might need to apply LayerNorm here.
        # GPT-2's lm_head can take the hidden state directly.
        early_logits = model.lm_head(early_hidden_state)
        late_logits = model.lm_head(late_hidden_state)

        # 6. Extract the logit specifically for our target token
        early_target_logit = early_logits[target_token_id].item()
        late_target_logit = late_logits[target_token_id].item()

        # 7. THE DOLA OPERATION: Subtract Reflex from Reasoning
        # This isolates the higher-order contextual features from raw statistical bias.
        dola_score = late_target_logit - early_target_logit

    # Output the analytical breakdown
    print(f"\n--- True DoLa Analysis for token: '{target_token_str}' ---")
    print(f"Early Layer [{early_layer_idx}] Logit (Reflex):   {early_target_logit:.4f}")
    print(f"Late Layer [Final] Logit (Reasoning): {late_target_logit:.4f}")
    print(f"DoLa Score (Late - Early):            {dola_score:.4f}\n")
    
    if dola_score > 0:
        print("Conclusion: GAIN. The later layers actively promoted this token over the reflex.")
    else:
        print("Conclusion: INHIBITION. The later layers actively suppressed the initial reflex.")

# Example Usage:
# true_dola_classifier("The bank is completely flooded. Is this a financial institution? Answer: ", "Yes", early_layer_idx=2)
