import numpy as np 

def proportion_normalization(data, axis=0):
    """
    Normalizes data using the Proportion method (Sum normalization).
    Formula: p_ij = x_ij / sum(x_ij)
    
    Args:
        data (np.array or list): The raw data matrix.
        axis (int): 0 to normalize columns (standard for criteria weighting), 
                    1 to normalize rows.
                    
    Returns:
        np.array: The P_ij matrix where the sum along the axis is 1.
    """
    X = np.array(data, dtype=float)
    
    # Calculate the sum of each column (or row if axis=1)
    # This corresponds to the sigma term in the denominator
    sums = np.sum(X, axis=axis)
    
    # Avoid division by zero
    # If a column sums to 0, we can't normalize it. Replace 0 with 1 temporarily to avoid NaN.
    sums[sums == 0] = 1 
    
    # Divide original matrix by the sums
    # Broadcasting ensures each element is divided by its corresponding column/row sum
    if axis == 0:
        P = X / sums[None, :]
    else:
        P = X / sums[:, None]
        
    return P

def calculate_entropy_weights(P):
    """
    Calculates Entropy (E) and Weights (W) from the normalized proportion matrix P.
    
    Args:
        P (np.array): Normalized matrix (from the previous step), where columns sum to 1.
        
    Returns:
        tuple: (Entropy Vector E, Weight Vector W)
    """
    # n is the number of alternatives (rows)
    n, m = P.shape
    
    # 1. Define constant k
    # If n=1, log(n)=0, causing div/0. In that case, entropy is 0.
    if n > 1:
        k = 1.0 / np.log(n)
    else:
        k = 0

    # 2. Calculate P * ln(P)
    # We use np.where to handle the case where P=0 safely (0 * ln(0) = 0)
    # This avoids RuntimeWarnings for log(0)
    log_p = np.where(P > 0, np.log(P), 0)
    product = P * log_p
    
    # 3. Sum specific entropy for each column (axis=0)
    # The negative sign is part of the formula: -k * sum(...)
    S_j = -k * np.sum(product, axis=0)
    
    # S_j is our Entropy vector (E)
    E = S_j
    
    # 4. Calculate Divergence (d)
    # d = 1 - E
    d = 1 - E
    
    # 5. Calculate Weights (W)
    # w = d / sum(d)
    total_d = np.sum(d)
    
    if total_d == 0:
        # If all entropies are 1 (data is identical in every column), weights are equal
        W = np.ones(m) / m
    else:
        W = d / total_d
        
    return E, W

def calculate_final_scores(P, W):
    """
    Calculates the final Fintech Index score for each bank.
    
    Args:
        P (np.array): The normalized data matrix (Banks x Keywords).
        W (np.array): The calculated weights for each keyword.
        
    Returns:
        np.array: A 1D array of final scores for each bank.
    """
    # Multiply each column (keyword) in the normalized matrix by its specific weight
    weighted_matrix = P * W
    
    # Sum the weighted scores across the rows (axis=1) to get the final score per bank
    final_scores = np.sum(weighted_matrix, axis=1)
    
    return final_scores

# --- Usage ---
# Raw data should be comprised of alternatives (ROWS) and criterion (COLLUMNS)
# In the case of Fintech data, the ROWS should be the names of the firms and 
# the COLLUMNS should be the keywords
# sample data from this video: https://www.youtube.com/watch?v=8OeXP9tAadM
'''
raw_data = [
    [2, 1500, 20000, 5.5, 5, 9], 
    [2.5, 2700, 18000, 6.5, 3, 5], 
    [1.8, 2000, 21000, 4.5, 7, 7], 
    [2.2, 1800, 20000, 5, 5, 5]
]

# axis=0 means we calculate the proportion of each alternative PER criterion (Column)
p_matrix = proportion_normalization(raw_data, axis=0)

print("Proportion Matrix (P_ij):\n", np.round(p_matrix, 4))

# Verification: The columns should sum to 1
print("Column Sums (Should be 1):", np.sum(p_matrix, axis=0))

entropy_vals, weights = calculate_entropy_weights(p_matrix)

print("\n1. Entropy Values (E_j):")
print(np.round(entropy_vals, 4))
print("\n2. Final Weights (W_j):")
print(np.round(weights, 4))

# Check: Weights should sum to 1
print("\nSum of Weights:", np.round(np.sum(weights), 2))
'''