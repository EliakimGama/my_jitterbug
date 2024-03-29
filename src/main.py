from __future__ import division, print_function

from datetime import timedelta
from jitterbug import *
from supervised_models import TM,SVM,RF,DT,NB,LR
from pdb import set_trace

import matplotlib.pyplot as plt
from os import listdir

from collections import Counter

import pandas as pd
from demos import cmd
try:
   import cPickle as pickle
except:
   import pickle
import warnings
warnings.filterwarnings('ignore')


def parse(path = "../data/"):
    for file in listdir(path):
        df = pd.read_csv("../data/"+file)
        df.rename(columns={'commenttext':'Abstract'}, inplace=True)
        df['label'] = ["no" if type=="WITHOUT_CLASSIFICATION" else "yes" for type in df["classification"]]
        df['ID'] = range(len(df))
        df = df[["ID","projectname","classification","Abstract","label",]]
        with open("../new_data/original/"+file, 'w', newline='\r\n') as f:
            df.to_csv(f, index=False)

def find_patterns(target='apache-ant-1.7.0'):
    data=load_csv(path="../new_data/original/")
    jitterbug = Jitterbug(data,target)
    patterns = jitterbug.find_patterns()
    print("Patterns:")
    print(patterns)
    print("Precisions on training set:")
    print({p: jitterbug.easy.precs[i] for i,p in enumerate(patterns)})

def validate_ground_truth(target='apache-ant-1.7.0'):
    data=load_csv(path="../new_data/original/")
    jitterbug = Jitterbug(data,target)
    patterns = jitterbug.find_patterns()
    jitterbug.easy_code(patterns)
    jitterbug.output_conflicts(output="../new_data/conflicts/")

def summarize_validate(input = "../new_data/validate/",output="../results/"):
    data=load_csv(input)
    columns = ["Double Check"]+list(data.keys())
    result = {}
    result["Double Check"] = ["yes (Easy)","no (GT)"]
    for project in data:
        count = Counter(data[project]["validate"])
        result[project]=[count["yes"],count["no"]]
    df = pd.DataFrame(data=result,columns=columns)
    df.to_csv(output+"validate_sum.csv", line_terminator="\r\n", index=False)

def correct_ground_truth(validated="../new_data/validate/", output="../new_data/corrected/"):
    data = load_csv(path="../new_data/original/")
    data_validated = load_csv(path=validated)
    for project in data:
        for id in data_validated[project][data_validated[project]["validate"]=="yes"]["ID"]:
            data[project]["label"][id]="yes"
        data[project].to_csv(output+project+".csv", line_terminator="\r\n", index=False)

        stats = Counter(data_validated[project]["validate"])
        ratio = float(stats["yes"])/(stats["yes"]+stats["no"])
        print(project)
        print(ratio)

def Easy_results(source="corrected",output="../results/"):
    input = "../new_data/"+source+"/"
    data=load_csv(path=input)
    results = {"Metrics":["Precision","Recall","F1"]}
    for target in data:
        jitterbug = Jitterbug(data,target)
        patterns = jitterbug.find_patterns()
        print(patterns)
        print(jitterbug.easy.precs)
        stats = jitterbug.test_patterns(output=True)
        stats["t"] = len(data[target][data[target]["label"]=="yes"])
        prec = float(stats['tp'])/stats['p']
        rec = float(stats['tp'])/stats['t']
        f1 = 2*prec*rec/(prec+rec)
        results[target]=[prec,rec,f1]
    df = pd.DataFrame(data=results,columns=["Metrics"]+list(data.keys()))
    df.to_csv(output+"step1_Easy_"+source+".csv", line_terminator="\r\n", index=False)

def MAT_results(source="corrected",output="../results/"):
    input = "../new_data/"+source+"/"
    data=load_csv(path=input)
    results = {"Metrics":["Precision","Recall","F1"]}
    for target in data:
        mat = MAT(data,target)
        mat.preprocess()
        mat.find_patterns()
        stats = mat.test_patterns()
        stats["t"] = len(data[target][data[target]["label"]=="yes"])
        prec = float(stats['tp'])/stats['p']
        rec = float(stats['tp'])/stats['t']
        f1 = 2*prec*rec/(prec+rec)
        results[target]=[prec,rec,f1]
    df = pd.DataFrame(data=results,columns=["Metrics"]+list(data.keys()))
    df.to_csv(output+"step1_MAT_"+source+".csv", line_terminator="\r\n", index=False)

def fitness_pattern(pattern='xxx'):
    data=load_csv(path="../new_data/original/")
    fitness = {}
    for target in data:
        jitterbug = Jitterbug(data,target)
        p_id = list(jitterbug.easy.voc).index(pattern)
        poses = np.where(np.array(jitterbug.easy.y_label)== "yes")[0]
        count_tp = np.array(np.sum(jitterbug.easy.test_data[poses], axis=0))[0][p_id]
        count_p = np.array(np.sum(jitterbug.easy.test_data, axis=0))[0][p_id]
        fitness[target] = np.nan_to_num(count_tp * (count_tp / count_p) ** 3)
    print(fitness)



def rest_results(seed=0,input="../new_data/rest/",output="../results/"):
    treatments = ["LR","DT","RF","SVM","NB","TM"]
    data=load_csv(path=input)
    columns = ["Treatment"]+list(data.keys())

    # Supervised Learning Results
    result = {target: [supervised_model(data,target,model=model,seed=seed) for model in treatments] for target in data}
    result["Treatment"] = treatments

    to_dump = {key: {"RF": result[key][2], "TM": result[key][5]} for key in data}

    # Output results to tables
    metrics = result[columns[-1]][0].keys()
    for metric in metrics:
        df = {key: (result[key] if key=="Treatment" else [dict[metric] for dict in result[key]]) for key in result}
        pd.DataFrame(df,columns=columns).to_csv(output+"rest_"+metric+".csv", line_terminator="\r\n", index=False)

    # Hard Results (continuous learning)
    APFD_result = {}
    AUC_result = {}
    for target in data:
        APFD_result[target] = []
        AUC_result[target] = []
        for model in treatments[:-1]:
            jitterbug = Jitterbug_hard(data,target,model=model,seed=seed)
            stats = jitterbug.eval()
            APFD_result[target].append(stats['APFD'])
            AUC_result[target].append(stats['AUC'])
            if model=="RF":
                to_dump[target]["Hard"] = stats

    with open("../dump/rest_result.pickle","wb") as f:
        pickle.dump(to_dump,f)
    APFD_result["Treatment"] = treatments[:-1]
    AUC_result["Treatment"] = treatments[:-1]
    pd.DataFrame(APFD_result,columns=columns).to_csv(output+"rest_APFD_Hard.csv", line_terminator="\r\n", index=False)
    pd.DataFrame(AUC_result,columns=columns).to_csv(output+"rest_AUC_Hard.csv", line_terminator="\r\n", index=False)


def estimate_results(seed=0,T_rec=0.90,model="RF",input="../new_data/rest/"):
    data=load_csv(path=input)
    # Hard Results
    for target in data:
        jitterbug = Jitterbug_hard(data,target,est=True,T_rec=T_rec,model=model,seed=seed)
        jitterbug.hard.plot(T_rec=T_rec)


def overall_results(seed=0,input="../new_data/corrected/",output="../results/"):
    data=load_csv(path=input)
    columns = ["Treatment"] + list(data.keys())
    APFDs = {"Treatment":["Jitterbug","Easy+RF","Hard","MAT+RF","TM","RF"]}
    AUCs = {"Treatment":["Jitterbug","Easy+RF","Hard","MAT+RF","TM","RF"]}
    results = {}
    for target in data:
        results[target]={}
        APFDs[target] = []
        AUCs[target] = []

        print(target)
        start = time.time()

        stats = two_step_Jitterbug(data,target,seed=seed)
        APFDs[target].append(stats["APFD"])
        AUCs[target].append(stats["AUC"])
        results[target]["Jitterbug"] = stats

        end = time.time()
        print("Jitterbug")
        print(str(timedelta(seconds=end-start)))
        start = end

        stats = two_step_Easy(data,target,seed=seed)
        APFDs[target].append(stats["APFD"])
        AUCs[target].append(stats["AUC"])
        results[target]["Easy+RF"] = stats

        end = time.time()
        print("Easy+RF")
        print(str(timedelta(seconds=end - start)))
        start = end

        stats = Jitterbug_hard(data,target,est=False,seed=seed).eval()
        APFDs[target].append(stats["APFD"])
        AUCs[target].append(stats["AUC"])
        results[target]["Hard"] = stats

        end = time.time()
        print("Hard")
        print(str(timedelta(seconds=end - start)))
        start = end

        stats = two_step_MAT(data,target,seed=seed)
        APFDs[target].append(stats["APFD"])
        AUCs[target].append(stats["AUC"])
        results[target]["MAT+RF"] = stats

        end = time.time()
        print("MAT+RF")
        print(str(timedelta(seconds=end - start)))
        start = end

        stats = supervised_model(data,target, model = "RF",seed=seed)
        APFDs[target].append(stats["APFD"])
        AUCs[target].append(stats["AUC"])
        results[target]["RF"] = stats

        end = time.time()
        print("RF")
        print(str(timedelta(seconds=end - start)))
        start = end

        stats = supervised_model(data,target, model = "TM",seed=seed)
        APFDs[target].append(stats["APFD"])
        AUCs[target].append(stats["AUC"])
        results[target]["TM"] = stats

        end = time.time()
        print("TM")
        print(str(timedelta(seconds=end - start)))

    with open("../dump/overall_result.pickle","wb") as f:
        pickle.dump(results,f)
    pd.DataFrame(APFDs,columns=columns).to_csv(output+"overall_APFD.csv", line_terminator="\r\n", index=False)
    pd.DataFrame(AUCs,columns=columns).to_csv(output+"overall_AUC.csv", line_terminator="\r\n", index=False)



def stopping_results(which="corrected",seed=0,input="../new_data/",output="../results/"):
    data=load_csv(path=input+which+"/")
    columns = ["Metrics"] + list(data.keys())
    result = {"Metrics":["Precision","Recall","F1","Cost"]}
    for target in data:
        result[target] = []
        stats = two_step_Jitterbug(data,target, est = True, T_rec=0.9, seed=seed)
        for metric in result["Metrics"]:
            result[target].append(stats[metric])
    pd.DataFrame(result,columns=columns).to_csv(output+"stopping_0.9_"+which+".csv", line_terminator="\r\n", index=False)



def plot_recall_cost(which = "overall"):
    path = "../dump/"+which+"_result.pickle"
    with open(path,"rb") as f:
        results = pickle.load(f)

    font = {'family': 'normal',
            'weight': 'bold',
            'size': 20}

    plt.rc('font', **font)
    paras = {'lines.linewidth': 5, 'legend.fontsize': 20, 'axes.labelsize': 30, 'legend.frameon': False,
             'figure.autolayout': True, 'figure.figsize': (16, 8)}

    plt.rcParams.update(paras)

    lines = ['-',':','--',(0,(4,2,1,2)),(0,(3,2)),(0,(2,1,1,1))]

    for project in results:
        fig = plt.figure()
        for i,treatment in enumerate(results[project]):
            plt.plot(results[project][treatment]["CostR"], results[project][treatment]["TPR"], linestyle = lines[i], label=treatment)
        plt.legend()
        plt.ylabel("Recall")
        plt.xlabel("Cost")
        plt.grid()
        plt.savefig("../figures_"+which+"/" + project + ".png")
        plt.close(fig)



# utils

def load_csv(path="../new_data/original/"):
    data={}
    for file in listdir(path):
        if file==".DS_Store":
            continue
        df = pd.read_csv(path+file, encoding='latin1')
        data[file.split(".csv")[0]] = df
    return data

def supervised_model(data, target, model = "RF", seed = 0):
    np.random.seed(seed)
    treatments = {"RF":RF,"SVM":SVM,"LR":LR,"NB":NB,"DT":DT,"TM":TM}
    treatment = treatments[model]
    clf = treatment(data,target)
    clf.preprocess()
    clf.train()
    result = clf.eval()
    return result

def Jitterbug_hard(data, target, est = False, T_rec=0.90, model = "RF", seed = 0):
    np.random.seed(seed)
    jitterbug=Jitterbug(data,target)
    jitterbug.ML_hard(model=model, est=est, T_rec=T_rec)
    return jitterbug


def two_step_Jitterbug(data, target, model = "RF", est = False, T_rec = 0.9, seed = 0):
    np.random.seed(seed)
    jitterbug=Jitterbug(data,target)

    jitterbug.find_patterns()
    jitterbug.easy_code()
    jitterbug.test_patterns()

    jitterbug.ML_hard(model = model, est = est, T_rec = T_rec)
    stats = jitterbug.eval()
    return stats

def two_step_MAT(data, target, model = "RF", seed = 0):
    np.random.seed(seed)
    mat = MAT_Two_Step(data,target)
    mat.find_patterns()
    mat.easy_code()
    mat.test_patterns()
    mat.ML_hard(model = model)
    stats = mat.eval()
    return stats

def two_step_Easy(data, target, model = "RF", seed = 0):
    np.random.seed(seed)
    easy = Easy_Two_Step(data,target)
    easy.find_patterns()
    easy.easy_code()
    easy.test_patterns()
    easy.ML_hard(model = model)
    stats = easy.eval()
    return stats



def apply_Jitterbug(train_path = "../new_data/corrected/", test_path = "../httpd/", test_file = "httpd.csv"):
    data = load_csv(path=train_path)
    test_df = pd.read_csv(test_path+test_file)
    target = test_file.split(".csv")[0]
    data[target] = test_df

    jitterbug=Jitterbug(data,target)

    # Learn patterns for easy-to-find SATDs
    jitterbug.find_patterns()
    #
    jitterbug.easy_code()
    jitterbug.output_target(test_path)

    # Find the hard-to-find SATDs interactively
    jitterbug.apply_hard(est=True)
    while True:
        jitterbug.query_hard(tmp = "../httpd/http_query.csv", output = "../httpd/httpd_rest_coded.csv", batch_size = 100)
        set_trace()

if __name__ == "__main__":
    eval(cmd())