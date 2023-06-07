import numpy
import os
import pickle
import sys

import numpy as np
import torch
from sklearn import metrics
from sklearn.cluster import KMeans
from transformers import BertTokenizer, AutoModel
import  sys
sys.path.append("..")
from config import BertAndToken  as bt
from config import Cluster as cf

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
tokenizer = None
model = None


from sklearn.manifold import TSNE
import matplotlib.pyplot as plt


def fun(vector, corpus,pool_type):
    tsne = TSNE(n_components=2, init='pca', verbose=1)
    embedd = tsne.fit_transform(vector)
    plt.figure(figsize=(7, 7))
    plt.rcParams['savefig.dpi'] = 1000  # 图片像素
    plt.rcParams['figure.dpi'] = 1000
    for i, label in enumerate(corpus):
        x, y = embedd[i, :]
        plt.scatter(x, y)
    for i in range(len(corpus)):
        x = embedd[i][0]
        y = embedd[i][1]
        plt.text(x, y, corpus[i])
    plt.savefig("./scbert_{}.png".format(pool_type))
    #plt.show()
def fun2(vec,y,pool_type):
    tsne = TSNE(n_components=2, random_state=0)
    embedd = tsne.fit_transform(vec)
    plt.figure(figsize=(7, 7))
    plt.rcParams['savefig.dpi'] = 1000  # 图片像素
    plt.rcParams['figure.dpi'] = 1000
    colors = ['r', 'g', 'b', 'c', 'm']  # 五个类别分别用五种颜色标记
    markers = ['o', 's', 'x', '^', '*']
    for i, c, m in zip(np.unique(y), colors, markers):
        plt.scatter(embedd[y == i, 0], embedd[y == i, 1], c=c, marker=m, label=y[i])
    plt.legend()
    # plt.show()
    plt.savefig("./scbert_{}.png".format(pool_type))

def get_sentence_embedding(sentece, pooler_type):
    inputs = tokenizer(
        [sentece],
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)
        hidden_states = outputs.hidden_states
        attention_mask = inputs['attention_mask']
        last_hidden = outputs.hidden_states[-1]
        embeddings = []
        if pooler_type == "avg":
            embeddings = ((last_hidden * attention_mask.unsqueeze(-1)).sum(1) / attention_mask.sum(-1).unsqueeze(-1))
        elif pooler_type == "avg_first_last":
            first_hidden = hidden_states[0]
            last_hidden = hidden_states[-1]
            pooled_result = ((first_hidden + last_hidden) / 2.0 * attention_mask.unsqueeze(-1)).sum(
                1) / attention_mask.sum(
                -1).unsqueeze(-1)
            embeddings = pooled_result
        elif pooler_type == "avg_top2":
            second_last_hidden = hidden_states[-2]
            last_hidden = hidden_states[-1]
            pooled_result = ((last_hidden + second_last_hidden) / 2.0 * attention_mask.unsqueeze(-1)).sum(
                1) / attention_mask.sum(-1).unsqueeze(-1)
            embeddings = pooled_result
        return embeddings.cpu().numpy()


def get_cluster_data(path):
    if os.path.exists(os.path.join(path, "cluster.pkl")):
        with open(os.path.join(path, "cluster.pkl"), 'rb') as f:
            lines = pickle.load(f)
    if os.path.exists(os.path.join(path, "label.pkl")):
        with open(os.path.join(path, "label.pkl"), 'rb') as f:
            labels = pickle.load(f)
    return lines, labels


def cluster_k_means(true_label, data, pooler_type):
    class_num = len(set(true_label))
    true_label = numpy.array(true_label)
    data = numpy.array(data)
    len_label = len(true_label)
    data = data.reshape((len_label, 768))
    clf = KMeans(n_clusters=class_num, max_iter=100, init="k-means++", tol=1e-6)
    _ = clf.fit(data)
    # source = list(clf.predict(data))
    predict_label = clf.labels_

    ARI = metrics.adjusted_rand_score(true_label, predict_label)
    print("embedding_type:", pooler_type)
    print("adjusted_rand_score: ", ARI)


def get_embeddings(path, output_dir, pooler_type, save=False):
    if os.path.exists(os.path.join(output_dir, "cluster_embedding" + pooler_type + ".pkl")):
        with open(os.path.join(path, "cluster_embedding" + pooler_type + ".pkl"), 'rb') as f:
            cluster_embeddings = pickle.load(f)
        with open(os.path.join(path, "cluster_label" + pooler_type + ".pkl"), 'rb') as f:
            labels = pickle.load(f)
        return cluster_embeddings, labels
    else:
        cluster_embeddings = []
        labels_new = []
        samples, labels = get_cluster_data(path)
        for sample in samples:
            embedding = get_sentence_embedding(sample['value'], pooler_type)
            cluster_embeddings.append(embedding)
            labels_new.append(sample['label'])
        if save:
            with open(os.path.join(output_dir, "cluster_embedding" + pooler_type + ".pkl"), 'wb') as f:
                pickle.dump(cluster_embeddings, f)
            with open(os.path.join(output_dir, "cluster_label" + pooler_type + ".pkl"), 'wb') as f:
                pickle.dump(labels_new, f)
        return cluster_embeddings, labels


if __name__ == '__main__':
    cluster_path = cf.cluster_construct_data_path
    output_dir = cluster_path
    args = sys.argv
    if len(args) == 1:
        pooler_type = "avg_first_last"  # avg,avg_top2,avg_first_last
        tokenizer = BertTokenizer.from_pretrained(bt.bert_train_output)
        model = AutoModel.from_pretrained(bt.bert_train_output)
        model.to(device)
    else:
        pooler_type = args[1]
    if len(args) ==2:
        if args[2]== "mirror_bert":
            tokenizer = BertTokenizer.from_pretrained(bt.mirrot_bert)
            model = AutoModel.from_pretrained(bt.mirrot_bert)
        else:
            print("first args,you can choose [avg_first_last,avg_top2, avg], second arg you choose one in :[mirror_bert],solibert model is default")
            sys.exit()
    embeddings, labels = get_embeddings(cluster_path, output_dir, pooler_type, False)

    # print(labels)
    print("T-SNE")
    # print(embeddings.shape)
    ten_embeddings = []
    ten_labels = [3,5,7,9,10]
    new_labels = []
    for i in range(len(embeddings)):
        if labels[i] in ten_labels:
            ten_embeddings.append(embeddings[i])
            new_labels.append(labels[i])
    ten_embeddings = numpy.array(ten_embeddings)
    ten_labels = numpy.array(new_labels)
    ten_embeddings = ten_embeddings.squeeze(-2)
    ten_embeddings = numpy.array(ten_embeddings)
    print(ten_embeddings[0])
    fun(ten_embeddings, ten_labels,pooler_type)
    print("start cluster")
    cluster_k_means(labels, embeddings, pooler_type)
