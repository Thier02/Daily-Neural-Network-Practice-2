import numpy as np,sys
from load_data import load_mnist
import matplotlib.pyplot as plt

np.random.seed(1)

# Set global parameters
NUM_POINTS = 500            # Number of samples from MNIST
CLASSES_TO_USE = [0, 1, 8,5,3]  # MNIST classes to use
PERPLEXITY = 20
SEED = 1                    # Random seed
MOMENTUM = 0.9
LEARNING_RATE = 10.
NUM_ITERS = 500             # Num iterations to train for
TSNE = False                # If False, Symmetric SNE
NUM_PLOTS = 5               # Num. times to plot in training


def neg_distance(X):
    X_sum = np.sum(X**2,1)
    distance = np.reshape(X_sum,[-1,1])
    return -(distance - 2*X.dot(X.T)+distance.T) 

def softmax_max(X,diag=True):
    X_exp = np.exp(X - X.max(1).reshape([-1, 1]))
    X_exp = X_exp + 1e-10
    if diag: np.fill_diagonal(X_exp, 0.)
    # X_exp = X_exp + 1e-10
    return X_exp/X_exp.sum(1).reshape([-1, 1])

def calc_prob_matrix(distances, sigmas=None):
    """Convert a distances matrix to a matrix of probabilities."""
    if sigmas is not None:
        two_sig_sq = 2. * sigmas.reshape([-1, 1]) ** 2
        return softmax_max(distances / two_sig_sq)
    else:
        return softmax_max(distances)

def perplexity(distances, sigmas):
    """Wrapper function for quick calculation of 
    perplexity over a distance matrix."""
    prob_matrix = calc_prob_matrix(distances, sigmas)
    entropy = -np.sum(prob_matrix * np.log2(prob_matrix + 1e-10), 1)
    perplexity = 2.0 ** entropy
    return perplexity

def binary_search(distance_vec, target, max_iter=20000,tol=1e-13, lower=1e-10, upper=1e10):
    """Perform a binary search over input values to eval_fn.
    # Arguments
        eval_fn: Function that we are optimising over.
        target: Target value we want the function to output.
        tol: Float, once our guess is this close to target, stop.
        max_iter: Integer, maximum num. iterations to search for.
        lower: Float, lower bound of search range.
        upper: Float, upper bound of search range.
    # Returns:
        Float, best input value to function found during search.
    """
    for i in range(max_iter):
        guess = (lower + upper) / 2.
        val = perplexity(distance_vec,np.array(guess))
        if val > target:
            upper = guess
        else:
            lower = guess
        if np.abs(val - target) <= tol:
            break
    return guess

def find_optimal_sigmas(distances, target_perplexity):
    """For each row of distances matrix, find sigma that results
    in target perplexity for that role."""
    sigmas = [] 
    # For each row of the matrix (each point in our dataset)
    for i in range(distances.shape[0]):
        # Binary search over sigmas to achieve target perplexity
        correct_sigma = binary_search(distances[i:i+1, :], target_perplexity)
        # Append the resulting sigma to our output array
        sigmas.append(correct_sigma)
    return np.array(sigmas)

def q_joint(Y):
    """Given low-dimensional representations Y, compute
    matrix of joint probabilities with entries q_ij."""
    # Get the distances from every point to every other
    distances = neg_distance(Y)
    # Take the elementwise exponent
    exp_distances = np.exp(distances)
    # Fill diagonal with zeroes so q_ii = 0
    np.fill_diagonal(exp_distances, 0.)
    # Divide by the sum of the entire exponentiated matrix
    return exp_distances / np.sum(exp_distances).reshape([-1,1])

def p_conditional_to_joint(P):
    """Given conditional probabilities matrix P, return
    approximation of joint distribution probabilities."""
    return (P + P.T) / (2. * P.shape[0])

def p_joint(X, target_perplexity):
    """Given a data matrix X, gives joint probabilities matrix.

    # Arguments
        X: Input data matrix.
    # Returns:
        P: Matrix with entries p_ij = joint probabilities.
    """
    # Get the negative euclidian distances matrix for our data
    distances = neg_distance(X)
    # Find optimal sigma for each row of this distances matrix
    sigmas = find_optimal_sigmas(distances, target_perplexity)
    # Calculate the probabilities based on these optimal sigmas
    p_conditional = calc_prob_matrix(distances, sigmas)
    # Go from conditional to joint probabilities matrix
    P = p_conditional_to_joint(p_conditional)
    return P

def q_tsne(Y):
    """t-SNE: Given low-dimensional representations Y, compute
    matrix of joint probabilities with entries q_ij."""
    distances = neg_distance(Y)
    inv_distances = np.power(1. - distances, -1)
    np.fill_diagonal(inv_distances, 0.)
    return inv_distances / np.sum(inv_distances), inv_distances

def sym_grad(P,Q,Y,one=None):
    """Estimate the gradient of the cost with respect to Y"""
    pq_diff = P - Q  # NxN matrix
    pq_expanded = np.expand_dims(pq_diff, 2)  #NxNx1
    y_diffs = np.expand_dims(Y, 1) - np.expand_dims(Y, 0)  #NxNx2
    grad = 4. * (pq_expanded * y_diffs).sum(1)  #Nx2
    return grad

def tsne_grad(P, Q, Y, inv_distances):
    """Estimate the gradient of t-SNE cost with respect to Y."""
    pq_diff = P - Q
    pq_expanded = np.expand_dims(pq_diff, 2)
    y_diffs = np.expand_dims(Y, 1) - np.expand_dims(Y, 0)

    # Expand our inv_distances matrix so can multiply by y_diffs
    distances_expanded = np.expand_dims(inv_distances, 2)

    # Multiply this by inverse distances matrix
    y_diffs_wt = y_diffs * distances_expanded

    # Multiply then sum over j's
    grad = 4. * (pq_expanded * y_diffs_wt).sum(1)
    return grad

# Set global parameters
NUM_POINTS = 1200            # Number of samples from MNIST
CLASSES_TO_USE = [0,6,7,9]  # MNIST classes to use
num_epoch = 1300
learning_rate = 0.09
print_size = 100
perplexity_number = 20

X, y = load_mnist('datasets/',digits_to_keep=CLASSES_TO_USE,N=NUM_POINTS)
W =  np.random.randn(NUM_POINTS,2) 
P = p_joint(X,perplexity_number)

# grad_sum_overtime = []
# for iter in range(2):
#     Q = q_joint(W)
#     grad = sym_grad(P,Q,W)
#     W = W - learning_rate * grad
#     grad_sum_overtime.append(grad.sum())
#     print('Current Iter: ',iter, ' Current Grad Sum : ',grad_sum_overtime[-1],end='\r')
#     if iter % print_size == 0 : print('\n---------------\n')

grad_sum_overtime = []
W2 = np.random.randn(NUM_POINTS,2) 
V2 = np.zeros_like(W2)
M2 = np.zeros_like(W2)
for iter in range(num_epoch):
    Q,inv_distances = q_tsne(W2)
    grad = tsne_grad(P,Q,W2,inv_distances)

    M2 = 0.9 * M2 + (1-0.9) * grad
    V2 = 0.999 * V2 + (1-0.999) * grad ** 2

    M_hat = M2/(1-0.9)
    V_hat = V2/(1-0.999)

    W2 = W2 - learning_rate/(np.sqrt(V_hat)+1e-8) * M_hat
    grad_sum_overtime.append(grad.sum())
    print('Current Iter: ',iter, ' Current Grad Sum : ',grad_sum_overtime[-1],end='\r')
    if iter % print_size == 0 : print('\n---------------\n')

color_dict = {
    0:'red',
    1:'blue',
    2:'green',
    3:'yellow',
    4:'purple',
    5:'grey',
    6:'black',
    7:'cyan',
    8:'pink',
    9:'skyblue',
}

plt.figure()
plt.suptitle(str(color_dict))
# plt.subplot(1, 2, 1)
# color_mapping = [color_dict[x] for x in y ]
# plt.scatter(W[:,0],W[:,1],c=color_mapping)
# plt.legend()
# plt.axis('off')

# plt.subplot(1, 2, 2)
color_mapping = [color_dict[x] for x in y ]
plt.scatter(W2[:,0],W2[:,1],c=color_mapping)
plt.legend()
plt.axis()
plt.show()


# -- end code --