import pandas as pd
import numpy as np
from gensim.models.keyedvectors import KeyedVectors
from sklearn.neighbors import NearestNeighbors
from scipy.spatial.distance import cosine

def load_data():
    try:
        # Grab a dataframe from Data cleaner folder and only import columns necessary for analyzing a user's repositories
        df = pd.read_csv('allReposCleaned.csv', usecols=['owner_user', 'name', 'description', 'language'])
        return df
    except FileNotFoundError:
        print("File not found.")
        return None

def preprocess_data(df):
    try:
        # count unique languges
        num_languages = df['language'].nunique()

        # Create list of unique languages with _ prefix
        languages = ['_' + language for language in df['language'].unique()]

        # one hot encode the languages and don't include the language prefix
        df = pd.get_dummies(df, columns=['language'], prefix='')

        # Group by 'owner_user' and aggregate
        aggregation_dict = {
            'name': lambda x: list(x),
            'description': lambda x: list(x)
        }

        # Add columns for languages
        for lang in languages:
            aggregation_dict[lang] = 'max'

        user_df = df.groupby('owner_user').agg(aggregation_dict).reset_index()

        # first we turn list of names and descriptions into a single string (so that it can later be utilized by the word2vec model)
        user_df['name'] = user_df['name'].apply(lambda x: ' '.join(str(i) for i in x) if isinstance(x, list) else '')
        user_df['description'] = user_df['description'].apply(lambda x: ' '.join(str(i) for i in x) if isinstance(x, list) else '')

        return user_df, languages
    except KeyError:
        print("KeyError occurred.")
        return None, None

def load_word2vec_model():
    try:
        # Load pre-trained Word2Vec model. Word Embeddings for the Software Engineering Domain, pre-trained on 15GB of Stack Overflow posts
        # Citation: Efstathiou Vasiliki, Chatzilenas Christos, & Spinellis Diomidis. (2018). Word Embeddings for the Software Engineering Domain [Data set]. Zenodo. https://doi.org/10.5281/zenodo.1199620
        word_vect = KeyedVectors.load_word2vec_format("./codecompasslib/PretrainedModels/SO_vectors_200.bin", binary=True)
        return word_vect
    except FileNotFoundError:
        print("File not found.")
        return None

def vectorize_text(text, word_vect):
    try:
        vector_sum = np.zeros(word_vect.vector_size)  # Initialize an array to store the sum of word vectors
        count = 0  # Initialize a count to keep track of the number of words found in the vocabulary
        for word in text.split():
            if word in word_vect.key_to_index:  # Check if the word is in the vocabulary
                vector_sum += word_vect[word]  # Add the word vector to the sum
                count += 1  # Increment the count
        if count > 0:
            return vector_sum / count  # Return the average of word vectors
        else:
            return vector_sum  # Return the zero vector if no words are found in the vocabulary
    except KeyError:
        print("KeyError occurred.")
        return None

def preprocess_user_df(user_df, word_vect):
    try:
        embedded_user_df = user_df.copy()
        embedded_user_df['name'] = user_df['name'].fillna('')  
        embedded_user_df['description'] = user_df['description'].fillna('')
        embedded_user_df['name_vector'] = embedded_user_df['name'].apply(lambda x: vectorize_text(x, word_vect))
        embedded_user_df['description_vector'] = embedded_user_df['description'].apply(lambda x: vectorize_text(x, word_vect))
        return embedded_user_df
    except KeyError:
        print("KeyError occurred.")
        return None

def preprocess_repos(neighbors_and_target_repos, word_vect):
    try:
        neighbors_and_target_repos_Copy = neighbors_and_target_repos.copy()
        neighbors_and_target_repos_Copy['name'] = neighbors_and_target_repos['name'].fillna('')
        neighbors_and_target_repos_Copy['description'] = neighbors_and_target_repos['description'].fillna('')
        neighbors_and_target_repos_Copy.loc[:, 'name_vector'] = neighbors_and_target_repos['name'].apply(lambda x: vectorize_text(x, word_vect))
        neighbors_and_target_repos_Copy.loc[:, 'description_vector'] = neighbors_and_target_repos['description'].apply(lambda x: vectorize_text(x, word_vect))
        neighbors_and_target_repos_Copy.drop(['name','description'], axis=1, inplace=True)
        return neighbors_and_target_repos_Copy * 1  # Multiply by 1 to convert booleans to int
    except KeyError:
        print("KeyError occurred.")
        return None

def calculate_cosine_dissimilarity(vec1, vec2):
    try:
        # Check for NaN values in the vectors
        if np.any(np.isnan(vec1)) or np.any(np.isnan(vec2)):
            return 0.5  # Return 0.5 dissimilarity if there are NaN values
        
        # Check for zero norms
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)
        if norm_vec1 < 1e-8 or norm_vec2 < 1e-8:
            return 0.5  # Return 0.5 dissimilarity if norms are close to zero
        
        # Calculate cosine dissimilarity
        return (-1) * cosine(vec1, vec2)
    except ValueError:
        print("ValueError occurred.")
        return None

def find_most_dissimilar_repos(target_user, target_repos, other_repos, languages, number_of_recommendations=1):
    try:
        dissimilar_repos = {} # Keys are the indices of the most dissimilar repos, values are the dissimilarity scores

        for row_o in other_repos.index:
            # Neighbor's repo vector which combines name and description vectors as well as languages of that repo
            neighbors_repo_vector = []
            # columns for languages and vector embeddings
            for columns in list(languages) + ['name_vector', 'description_vector']:
                if type(other_repos.at[row_o, columns]) == np.ndarray: # For embeddings
                    for element in other_repos.at[row_o, columns]:
                        neighbors_repo_vector.append(element)
                elif type(other_repos.at[row_o, columns]) == int: # For 0 and 1 values in languages
                    neighbors_repo_vector.append(other_repos.at[row_o, columns])

            dissimilarity_sum = 0 # To keep track of the sum of dissimilarities between the target user's repos (multiple) and the neighbor's repo (one)

            for row_t in target_repos.index:
                target_repo_vector = []
                for columns in list(languages) + ['name_vector', 'description_vector']:
                    if type(target_repos.at[row_t, columns]) == np.ndarray:
                        for element in target_repos.at[row_t, columns]:
                            target_repo_vector.append(element)
                    elif type(target_repos.at[row_t, columns]) == int:
                        target_repo_vector.append(target_repos.at[row_t, columns])


                dissimilarity_sum += calculate_cosine_dissimilarity(target_repo_vector, neighbors_repo_vector)

            average_dissimilarity = dissimilarity_sum / len(target_repos)
            dissimilar_repos[row_o] = average_dissimilarity
        # Return the n most dissimilar repos reverse sorted by dissimilarity score
        return sorted(dissimilar_repos.items(), key=lambda x: x[1], reverse=True)[:number_of_recommendations]
    except Exception as e:
        print("An error occurred:", str(e))
        return None

def get_user_index(df, target_user):
    try:
        return df[df['owner_user'] == target_user].index[0]
    except Exception as e:
        print("An error occurred:", str(e))
        return None

def main(user_input='AntiTyping', number_of_recommendations=1, return_neighbors=True):
    try:
        # Get the target user index and the target user from the user input
        target_user = user_input

        # Load data, preprocess it, and load the word2vec model, then preprocess the user dataframe and the neighbors dataframe.
        df = load_data()
        user_df, languages = preprocess_data(df)
        word_vect = load_word2vec_model()
        embedded_user_df = preprocess_user_df(user_df, word_vect) * 1 # Multiply by 1 to convert booleans to int
        target_user_index = int(get_user_index(embedded_user_df, target_user))
        vectors = []

        # Turn the embedded user dataframe into a list of vectors for every row/user
        for row in embedded_user_df.index: 
            vector = []
            # columns in langauges and vector embeddings
            for columns in list(languages) + ['name_vector', 'description_vector']:
                if type(embedded_user_df.at[row, columns]) == np.ndarray: # For embeddings
                    for element in embedded_user_df.at[row, columns]:
                        vector.append(element)
                elif type(embedded_user_df.at[row, columns]) == int: # For 0 and 1 values in languages
                    vector.append(embedded_user_df.at[row, columns])
            vectors.append(vector)

        # Fit the nearest neighbors model to find the most similar users to the target user
        k = 5
        nn_model = NearestNeighbors(n_neighbors=k, metric='euclidean')
        nn_model.fit(vectors)

        # Output the target user and the most similar users
        neighbors = nn_model.kneighbors([vectors[target_user_index]], return_distance=False)[0][1:]

        # return owner_names of neighbors if that is requested (this is used for testing purposes or if we want to change functionality of the model)
        if return_neighbors:
            print(embedded_user_df.iloc[neighbors]['owner_user'])
            return embedded_user_df.iloc[neighbors]['owner_user']

        # Gathering repos of all similar users and the target user
        neighbors_and_target = [target_user_index] + list(neighbors)
        neighbors_and_target = user_df.iloc[neighbors_and_target]
        df_one_hot_encoded = pd.get_dummies(df, columns=['language'], prefix='')
        neighbors_and_target_repos = df_one_hot_encoded[df_one_hot_encoded['owner_user'].isin(neighbors_and_target['owner_user'])]
        # vectorize name and description
        neighbors_and_target_repos = preprocess_repos(neighbors_and_target_repos, word_vect)

        # Split the target user's repos from the neighbors' repos
        target_repos = neighbors_and_target_repos[neighbors_and_target_repos['owner_user'] == target_user]
        neighbors_repos = neighbors_and_target_repos[neighbors_and_target_repos['owner_user'] != target_user]

        most_dissimilar_repos_info = find_most_dissimilar_repos(target_user, target_repos, neighbors_repos, languages, number_of_recommendations=number_of_recommendations)

        # Get the most dissimilar repos' indices and gather the information of the most dissimilar repos
        most_dissimilar_repo_info = df.iloc[[x[0] for x in most_dissimilar_repos_info]]

        recommendations = []

        # Generate a list of recommendation dictionaries
        for i in range(len(most_dissimilar_repo_info)):  
            recommendations.append({
                'name': most_dissimilar_repo_info['name'].iloc[i],
                'owner_user': most_dissimilar_repo_info['owner_user'].iloc[i],
                'description': most_dissimilar_repo_info['description'].iloc[i],
                'language': most_dissimilar_repo_info['language'].iloc[i]
            })
        for recommendation in recommendations:
            print('rec', recommendation)
        return recommendations
    except Exception as e:
        print("An error occurred:", str(e))
        return None

main()