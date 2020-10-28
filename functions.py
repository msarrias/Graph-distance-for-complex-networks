import numpy as np
import networkx as nx
from scipy.integrate import quad
import scipy.linalg as la
from matplotlib import pyplot as plt
import graphs as g
import random, time, math, json

def sort_eigenv(eigenvalues, eigenvectors):
    return sorted(zip(eigenvalues.real,
                      eigenvectors.T), key=lambda x: x[0])

def adj_degree_matrices(graph):
    A = (nx.adjacency_matrix(graph)).todense()
    D = np.diag(np.asarray(sum(A))[0])
    return A, D

def CTD_eigenv(vol_V, sorted_eigenv, D, eps):
    ctd_eign = {}
    for e in range(len(sorted_eigenv)):
        eigenv = np.sqrt( vol_V / ((sorted_eigenv[e][0] * np.diagonal(D)) + eps)) * sorted_eigenv[e][1]
        ctd_eign[e] = [sorted_eigenv[e][0], eigenv]
    return ctd_eign

def eigen_decomp_WS_models(watts_strogatz_graphs_dic, replicates, solve = "standard_L", ctd = False):
    eps=1e-10
    times_dic = {}
    eigenv_dic_p = {}
    A_dic = {}
    p = list(watts_strogatz_graphs_dic.keys())
    
    for ps in p:
        eigenv_dic = {}
        A_dic_p = {}
        tic_i = time.time() 
        times = []
        
        for j in range(replicates):
            graph = watts_strogatz_graphs_dic[ps][j]
            A_dic_p[j], D = adj_degree_matrices(graph)
            vol_V = sum(sum(D))
            
            if solve == "standard_L":
                eigenvalues, eigenvectors = la.eig(D - A_dic_p[j])
                eigenv_dic[j] = sort_eigenv(eigenvalues, eigenvectors) 
                
            if solve == "standard_Lsym":
                D_invsq = np.diag(1/np.sqrt(np.diag(D)))
                L_sym_rep = np.eye(D.shape[0]) - np.dot(D_invsq, A_dic_p[j]).dot(D_invsq)
                eigenvalues, eigenvectors = la.eig(L_sym_rep)
                if ctd:
                    eigenv_dic[j] = CTD_eigenv(vol_V, 
                                                 sort_eigenv(eigenvalues,
                                                             eigenvectors), D, eps)
                else:
                    eigenv_dic[j] = sort_eigenv(eigenvalues,eigenvectors)
                
            if solve == "generalized":
                eigenvalues, eigenvectors = la.eig(D - A_dic_p[j], D)
                if ctd:
                    eigenv_dic[j] = CTD_eigenv(vol_V, 
                                                 sort_eigenv(eigenvalues,
                                                             eigenvectors), D, eps)
                else:
                    eigenv_dic[j] = sort_eigenv(eigenvalues,eigenvectors)
                    
            
            tac_i = time.time()
            times.append((tac_i - tic_i) / 60)  
        A_dic[ps] =  A_dic_p
        eigenv_dic_p[ps] = eigenv_dic
        times_dic[ps] = times
    return (times_dic, A_dic, eigenv_dic_p)

def hamming_dist_models(A_p0, A_dic, replicates):
    haming_distance_dic = {}
    n=len(A_p0)
    p = list(A_dic.keys())
    for ps in p:
        A_ps = list(A_dic[ps].values())
        hamming_distances = []
        for j in range(replicates):
            hamming_distances.append(np.sum(np.abs(A_p0 - A_ps[j])) / (n * (n - 1)))
        haming_distance_dic[ps] = hamming_distances
    return haming_distance_dic

def spectral_distance(ctd_eignv_p0, ctd_eigenv_p_dic, replicates, print_ = True):
    G1 = ctd_eignv_p0
    Ni = len(G1)
    G2_dic = ctd_eigenv_p_dic
    p = list(G2_dic.keys())
    
    rep_distances_Lsym = {}
    integral_Lsym = []
    area_Lsym = []
    time_p_Lsym = []
    
    signs =[-1, 1]

    for idx, rp in enumerate(p):
        tic_p = time.time() 
        replicate_distance = []
        for rep in range(replicates):
            G2_dic_p  = G2_dic[rp][rep]
            Nj = len(G2_dic_p)
            Mij = min(Ni, Nj)
            integral_list = []
            for r in range(1, Mij):
                temp_integral = []
                for  sign_s in signs:
                    for sign_l in signs:
                        vri = sorted(g.normalize_eigenv(sign_s * G1[r][1]))
                        vrj = sorted(g.normalize_eigenv(sign_l * G2_dic_p[r][1]))
                        temp_integral.append(cdf_dist(vri, vrj))  
                integral_list.append(min(temp_integral))
            replicate_distance.append(sum(integral_list)/(Mij - 1))
        rep_distances_Lsym[rp] = replicate_distance
        tac_p = time.time()
        time_rp = (tac_p - tic_p) / 60
        if print_:
            print(f'd(G(0.1), G({rp})): {np.mean(rep_distances_Lsym[rp])}, ' \
                  f'took: {np.round(time_rp,4)} minutes')
        time_p_Lsym.append(time_rp)
        
    return (time_p_Lsym, rep_distances_Lsym)

def cdf_dist(vri, vrj):
    u = sorted(list(set(vri + vrj)))
    cdf_distance = 0
    vri_count = 0
    vrj_count = 0
    Ni = len(vri)
    Nj = len(vrj)
    for idx, sorted_elt in enumerate(u[1:]):
        # adding rectangle area, L * W
        cdf_distance += (u[idx] - u[idx - 1]) * abs((vri_count / Ni) - (vrj_count / Nj))
        if sorted_elt in vri:
            vri_count += 1
        if sorted_elt in vrj:
            vrj_count += 1
    return cdf_distance

def pairwise_spectral_dist(eigen_graphi, eigen_graphj):
    signs =[-1, 1]
    Ni = len(eigen_graphi)
    Nj = len(eigen_graphj)
    Mij = min(Ni, Nj)
    integral_list = []
    for r in range(1, Mij):
        temp_integral = []
        for  sign_s in signs:
            for sign_l in signs:
                vri = sorted(g.normalize_eigenv(sign_s * eigen_graphi[r][1]))
                vrj = sorted(g.normalize_eigenv(sign_l * eigen_graphj[r][1]))
                temp_integral.append(f.cdf_dist(vri, vrj))  
        integral_list.append(min(temp_integral))
    return(sum(integral_list)/(Mij - 1))

def savage_plot(mean_list, p_list,  p0, std_list, hd_avg_list, ylims_sgd, y_lims_hd):
    fig, ax1 = plt.subplots()
    color = 'tab:red'
    ax1.set_xlabel('p')
    ax1.set_ylabel('Spectral Graph Distance', color=color)
    ax1.plot(p_list, mean_list, '-o', color = color)
    ax1.axvline(x = p0, color = 'blue', linestyle = '--', label = "p_0 = "+ str(p0))
    ax1.fill_between(p_list, [mean_list[i] - std_list[i] for i in range(len(mean_list))],
                     [mean_list[i] + std_list[i] for i in range(len(mean_list))], 
                     color = 'lightgrey')
    ax1.set_ylim(ylims_sgd)
    ax1.tick_params(axis = 'y', labelcolor = color)

    ax2 = ax1.twinx()  

    color = 'tab:blue'
    ax2.set_ylabel('Hamming Distance ', color = color) 
    ax2.plot(p_list ,hd_avg_list, '-x', color = color)
    ax2.set_ylim(y_lims_hd)
    ax2.tick_params(axis = 'y', labelcolor = color)
    fig.tight_layout()
    plt.show()
    