#-*- coding:utf-8 -*-
# author:cjx
# datetime:2020/5/6 22:30


# Load a pre-trained model
from typing import Dict, Any, ValuesView

from gensim.models import Word2Vec
from sklearn.cluster import KMeans
import time
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from bs4 import BeautifulSoup
import re
from nltk.corpus import stopwords
import numpy as np
import os
from KaggleWord2VecUtility import KaggleWord2VecUtility


# Define a function to create bags of centroids
#
def create_bag_of_centroids(wordlist, word_centroid_map):
    #
    # The number of clusters is equal to the highest cluster index
    # in the word / centroid map
    num_centroids = max(word_centroid_map.values()) + 1
    #
    # Pre-allocate the bag of centroids vector (for speed)
    bag_of_centroids = np.zeros(num_centroids, dtype="float32")
    #
    # Loop over the words in the review. If the word is in the vocabulary,
    # find which cluster it belongs to, and increment that cluster count
    # by one
    for word in wordlist:
        if word in word_centroid_map:
            index = word_centroid_map[word]
            bag_of_centroids[index] += 1
    #
    # Return the "bag of centroids"
    return bag_of_centroids


if __name__ == '__main__':

    model = Word2Vec.load("300features_40minwords_10context")

    # ****** Run k-means on the word vectors and print a few clusters
    #

    start = time.time()  # Start time

    # Set "k" (num_clusters) to be 1/5th of the vocabulary size, or an
    # average of 5 words per cluster
    '''
    word_vectors = model.syn0
    error:model 没有 syn0 可以调用
    解决：word_vectors = model.wv.syn0
    原因：在Python2 转到 Python3 时，model的包本身做了修改
    '''
    word_vectors = model.wv.syn0
    '''
    num_clusters = word_vectors.shape[0] / 5
    TypeError: 'float' object cannot be interpreted as an integer
    解决：
    python2和python3中运算符的区别
    查看代码中是否含有/，
    python3的/结果含有浮点数！
    python2中的/等价于python3的//
    在python3中，//表示取整除 - 返回商的整数部分（向下取整）
    '''
    num_clusters = word_vectors.shape[0] // 5

    # Initalize a k-means object and use it to extract centroids
    print("Running K means")
    kmeans_clustering = KMeans(n_clusters=num_clusters)
    idx = kmeans_clustering.fit_predict(word_vectors)

    # Get the end time and print how long the process took
    end = time.time()
    elapsed = end - start
    print("Time taken for K Means clustering: ", elapsed, "seconds.")

    # Create a Word / Index dictionary, mapping each vocabulary word to
    # a cluster number
    word_centroid_map = dict(zip(model.wv.index2word, idx))

    # Print the first ten clusters
    for cluster in range(0, 10):
        #
        # Print the cluster number
        print("\nCluster %d" % cluster)
        #
        # Find all of the words for that cluster number, and print them out
        words = []

        for i in range(0, len(word_centroid_map.values())):
            '''
            error: word_centroid_map.values()[i]
            Dict 不支持直接获取下标，因为
            test: ValuesView[Any]= word_centroid_map.values()
            解决：将 ValuesView[Any] 强制转换成 list
            '''
            if (list(word_centroid_map.values())[i] == cluster):
                words.append(list(word_centroid_map.keys())[i])
        print(words)

    # Create clean_train_reviews and clean_test_reviews as we did before
    #

    # Read data from files
    train = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'labeledTrainData.tsv'), header=0,
                        delimiter="\t", quoting=3)
    test = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'testData.tsv'), header=0, delimiter="\t",
                       quoting=3)

    print("Cleaning training reviews")
    clean_train_reviews = []
    for review in train["review"]:
        clean_train_reviews.append(KaggleWord2VecUtility.review_to_wordlist(review, \
                                                                            remove_stopwords=True))

    print("Cleaning test reviews")
    clean_test_reviews = []
    for review in test["review"]:
        clean_test_reviews.append(KaggleWord2VecUtility.review_to_wordlist(review, \
                                                                           remove_stopwords=True))

    # ****** Create bags of centroids
    #
    # Pre-allocate an array for the training set bags of centroids (for speed)
    train_centroids = np.zeros((train["review"].size, num_clusters), \
                               dtype="float32")

    # Transform the training set reviews into bags of centroids
    counter = 0
    for review in clean_train_reviews:
        train_centroids[counter] = create_bag_of_centroids(review, \
                                                           word_centroid_map)
        counter += 1

    # Repeat for test reviews
    test_centroids = np.zeros((test["review"].size, num_clusters), \
                              dtype="float32")

    counter = 0
    for review in clean_test_reviews:
        test_centroids[counter] = create_bag_of_centroids(review, \
                                                          word_centroid_map)
        counter += 1

    # ****** Fit a random forest and extract predictions
    #
    forest = RandomForestClassifier(n_estimators=100)

    # Fitting the forest may take a few minutes
    print("Fitting a random forest to labeled training data...")
    forest = forest.fit(train_centroids, train["sentiment"])
    result = forest.predict(test_centroids)

    # Write the test results
    output = pd.DataFrame(data={"id": test["id"], "sentiment": result})
    output.to_csv("BagOfCentroids.csv", index=False, quoting=3)
    print("Wrote BagOfCentroids.csv")
