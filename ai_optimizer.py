from google import genai
from google.genai import types
import json
import os

def get_keyword_weights(found_keywords, missing_keywords, job_description):
    """
    Use Gemini to assign a relevance weight (1-10) for each keyword relative to the JD.
    """
    all_keywords = list(set(found_keywords + missing_keywords))
    
    prompt = f"""
    You are an ATS optimization expert. Given a list of keywords and a job description, 
    assign a relevance score from 1 (low) to 10 (business critical) for each keyword.
    
    Job Description:
    {job_description}
    
    Keywords:
    {", ".join(all_keywords)}
    
    Return ONLY a JSON object where keys are keywords and values are integer weights (1-10).
    Example: {{"Python": 10, "Excel": 3}}
    """
    
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        weights = json.loads(response.text)
        return {k: weights.get(k, 1) for k in all_keywords}
    except Exception as e:
        print(f"Error getting weights: {e}")
        return {k: 5 for k in all_keywords}

def calculate_score(current_keywords, weights, total_possible_weight):
    if not total_possible_weight:
        return 0
    
    current_weight = sum(weights.get(k, 0) for k in current_keywords)
    
    # We add a 1.5% 'Experience & Context' buffer that keywords alone can't fill.
    # This ensures a 'perfect' keyword match stops at ~98.5%.
    raw_score = (current_weight / total_possible_weight) * 100
    
    # Apply a realistic ceiling
    score = min(raw_score, 98.5)
    
    return round(score, 2)

def hill_climbing_optimize(found_keywords, missing_keywords, job_description, max_extra_keywords=5, target_score=90.0):
    """
    Classic Hill Climbing with constraints: 
    - Start with current found keywords.
    - Generate neighbors by adding a missing keyword or swapping a weak one for a strong one.
    - Move to the neighbor that gives the highest score increase.
    - Stop when:
        1. No better score is found.
        2. Maximum extra keywords have been added (max_extra_keywords).
        3. Target ATS score is reached or exceeded (target_score).
    """
    
    # --- Clean Buzzwords (Hard Filter) ---
    BUZZWORD_FILTER = {"motivated", "detail-oriented", "hard-working", "passionate", "team-player", "punctual"}
    found_keywords = [k for k in found_keywords if k.lower().strip() not in BUZZWORD_FILTER]
    missing_keywords = [k for k in missing_keywords if k.lower().strip() not in BUZZWORD_FILTER]
    
    weights = get_keyword_weights(found_keywords, missing_keywords, job_description)
    all_possible_keywords = set(found_keywords + missing_keywords)
    total_possible_weight = sum(weights.values())
    
    current_state = set(found_keywords)
    current_score = calculate_score(current_state, weights, total_possible_weight)
    
    original_score = current_score
    history = []
    added = []
    removed = []
    
    # We'll limit the resume size implicitly: we only add if it improves the score.
    # In a resume, adding a relevant keyword ALWAYS improves the score unless we have negative weights.
    # To make it "Hill Climbing", let's assume we can only have a certain number of keywords (e.g., len(found) + 5).
    # OR, we stop if the improvement is below a threshold.
    # Let's say we want to reach a target near 100% but iteratively.
    
    max_iterations = 20
    for _ in range(max_iterations):
        best_neighbor = None
        best_score = current_score
        improvement_type = None
        keyword_diff = None
        
        # Neighbor Type 1: Add a missing keyword (if under limit)
        if len(added) < max_extra_keywords:
            for k in missing_keywords:
                if k not in current_state:
                    neighbor = current_state | {k}
                    score = calculate_score(neighbor, weights, total_possible_weight)
                    if score > best_score:
                        best_score = score
                        best_neighbor = neighbor
                        improvement_type = "add"
                        keyword_diff = k
        
        # Neighbor Type 2: Replace a "weak" keyword (weight < 4) with a "strong" one (weight > 7)
        # This occurs even if we are at our max_extra_keywords limit.
        weak_keywords = [k for k in current_state if weights.get(k, 5) < 4]
        strong_missing = [k for k in missing_keywords if k not in current_state and weights.get(k, 5) > 7]
        
        for weak in weak_keywords:
            for strong in strong_missing:
                neighbor = (current_state - {weak}) | {strong}
                score = calculate_score(neighbor, weights, total_possible_weight)
                if score > best_score:
                    best_score = score
                    best_neighbor = neighbor
                    improvement_type = "replace"
                    keyword_diff = (weak, strong)
        
        if best_neighbor and best_score > current_score:
            if improvement_type == "add":
                added.append(keyword_diff)
                history.append(f"Added high-impact keyword: **{keyword_diff}** (Weight: {weights.get(keyword_diff)})")
            elif improvement_type == "replace":
                removed.append(keyword_diff[0])
                added.append(keyword_diff[1])
                history.append(f"Replaced weak keyword **{keyword_diff[0]}** with stronger **{keyword_diff[1]}**")
            
            current_state = best_neighbor
            current_score = best_score

            # Stop if we've reached or exceeded the target score
            if current_score >= target_score:
                history.append(f"Target score of {target_score}% reached.")
                break
        else:
            # Local maxima reached
            break
            
    return {
        "original_score": original_score,
        "optimized_score": current_score,
        "added": list(set(added)),
        "removed": list(set(removed)),
        "history": history
    }
