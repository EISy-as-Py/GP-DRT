# -*- coding: utf-8 -*-
"""
Created on Tue Dec 10 2019

@author: Jiapeng Liu, Francesco Ciucci (francesco.ciucci@ust.hk)
"""
################################################################################
# This python file includes all necessary equations for GP-DRT implemented in  #
# the paper "Liu, J., & Ciucci, F. (2019). The Gaussian process distribution   #
# of relaxation times: A machine learning tool for the analysis and prediction #
# of electrochemical impedance spectroscopy data. Electrochimica Acta, 135316."#
# If you find it is useful, please cite the paper and feel free to use and mod-#
# fy the code.                                                                 #
################################################################################

# imports
from math import exp
from math import pi
from math import log
from scipy import integrate
import numpy as np


# Define squared exponential kernel, $\sigma_f^2 \exp\left(-\frac{1}{2 \ell^2}\left(\xi-\xi^\prime\right)^2 \right)$
def kernel(xi, xi_prime, sigma_f, ell):
    return (sigma_f**2)*exp(-0.5/(ell**2)*((xi-xi_prime)**2))


# the function to be integrated in eq (65) of main text, omiting the constant part
# $\frac{\displaystyle e^{\Delta\xi_{mn}-\chi}}{1+\left(\displaystyle e^{\Delta\xi_{mn}-\chi}\right)^2} \frac{k(\chi)}{\sigma_f^2}$
def integrand_L_im(x, delta_xi, sigma_f, ell):
    kernel_part = 0.0
    sqr_exp = exp(-0.5/(ell**2)*(x**2))
    a = delta_xi-x
    if a>0:
        kernel_part = exp(-a)/(1.+exp(-2*a))
    else:
        kernel_part = exp(a)/(1.+exp(2*a))
    return kernel_part*sqr_exp


# the function to be integrated in eq (76) of main text, omiting the constant part
# $\frac{1}{2} \left(\chi+\Delta\xi_{mn}\right){\rm csch}\left(\chi+\Delta\xi_{mn}\right) \frac{k(\chi)}{\sigma_f^2}$
def integrand_L2_im(x, xi, xi_prime, sigma_f, ell):
    f = exp(xi)
    f_prime = exp(xi_prime)
    numerator = exp(x-0.5/(ell**2)*(x**2))*(x+xi_prime-xi)
    if x<0:
        numerator = exp(x-0.5/(ell**2)*(x**2))*(x+xi_prime-xi)
        denominator = (-1+((f_prime/f)**2)*exp(2*x))
    else:
        numerator = exp(-x-0.5/(ell**2)*(x**2))*(x+xi_prime-xi)
        denominator = (-exp(-2*x)+((f_prime/f)**2))
    return numerator/denominator


# derivative of integrand in eq (76) with respect to \ell 
# $\frac{1}{2} \left(\chi+\Delta\xi_{mn}\right){\rm csch}\left(\chi+\Delta\xi_{mn}\right) \frac{k(\chi)}{\sigma_f^2}\chi^2$
# omiting the $\ell^3$ in the denominator
def integrand_der_ell_L2_im(x, xi, xi_prime, sigma_f, ell):
    f = exp(xi)
    f_prime = exp(xi_prime)
    if x<0:
        numerator = (x**2)*exp(x-0.5/(ell**2)*(x**2))*(x+xi_prime-xi)
        denominator = (-1+((f_prime/f)**2)*exp(2*x))
    else:
        numerator = (x**2)*exp(-x-0.5/(ell**2)*(x**2))*(x+xi_prime-xi)
        denominator = (-exp(-2*x)+((f_prime/f)**2))
    return numerator/denominator


# assemble the covariance matrix K as shown in eq (18a), which consists of kenel distance between $\xi_n$ and $\xi_m$
def matrix_K(xi_n_vec, xi_m_vec, sigma_f, ell):

    N_n_freqs = xi_n_vec.size
    N_m_freqs = xi_m_vec.size

    K = np.zeros([N_n_freqs, N_m_freqs])

    for n in range(0, N_n_freqs):
        for m in range(0, N_m_freqs):
            K[n,m] = kernel(xi_n_vec[n], xi_m_vec[m], sigma_f, ell)

    return K


# assemble the matrix of eq (18b), added the term of $\frac{1}{\sigma_f^2}$ and factor $2\pi$ before $e^{\Delta\xi_{mn}-\chi}$
# only considering the case that $\xi_n$ and $\xi_m$ are identical, i.e., the matrice are symmetry square
def matrix_L_im_K(xi_n_vec, xi_m_vec, sigma_f, ell):
    
    assert np.array_equal(xi_n_vec, xi_m_vec), "vector xi_n_vec should be equal to vector xi_m_vec"
    xi_vec = xi_n_vec
    N_freqs = xi_vec.size
    L_im_K = np.zeros([N_freqs, N_freqs])

    for n in range(0, N_freqs):
        delta_xi = xi_vec[n]-xi_vec[0] + log(2*pi)
        integral, tol = integrate.quad(integrand_L_im, -np.inf, np.inf, epsabs=1E-12, epsrel=1E-12, args=(delta_xi, sigma_f, ell))
        np.fill_diagonal(L_im_K[n:, :], (sigma_f**2)*(integral))
        
        delta_xi = xi_vec[0]-xi_vec[n] + log(2*pi)
        integral, tol = integrate.quad(integrand_L_im, -np.inf, np.inf, epsabs=1E-12, epsrel=1E-12, args=(delta_xi, sigma_f, ell))
        np.fill_diagonal(L_im_K[:, n:], (sigma_f**2)*(integral))
    return L_im_K


# assemble the matrix of eq (18b), added the term of $\frac{1}{\sigma_f^2}$ and factor $2\pi$ before $e^{\Delta\xi_{mn}-\chi}$
# only considering the case that $\xi_n$ and $\xi_m$ are identical, i.e., the matrice are symmetry square
def matrix_L2_im_K(xi_n_vec, xi_m_vec, sigma_f, ell):
    
    assert np.array_equal(xi_n_vec, xi_m_vec), "vector xi_n_vec should be equal to vector xi_m_vec"
    xi_vec = xi_n_vec
    N_freqs = xi_vec.size
    L2_im_K = np.zeros([N_freqs, N_freqs])

    for n in range(0, N_freqs):
        xi = xi_vec[n]
        xi_prime = xi_vec[0]
        integral, tol = integrate.quad(integrand_L2_im, -np.inf, np.inf, epsabs=1E-12, epsrel=1E-12, args=(xi, xi_prime, sigma_f, ell))
        
        np.fill_diagonal(L2_im_K[n:, :], exp(xi_prime-xi)*(sigma_f**2)*integral)
        np.fill_diagonal(L2_im_K[:, n:], exp(xi_prime-xi)*(sigma_f**2)*integral)
            
    return L2_im_K

# calculate the negtive marginal log-likelihood (NMLL) of eq (31)
def NMLL_fct(theta, Z_exp, xi_vec):
    # load the initial value for parameters needed to optimize
    sigma_n = theta[0]
    sigma_f = theta[1]
    ell = theta[2]
    
    N_freqs = xi_vec.size
    Sigma = (sigma_n**2)*np.eye(N_freqs)                    # $\sigma_n^2 \mathbf I$
    
    L2_im_K = matrix_L2_im_K(xi_vec, xi_vec, sigma_f, ell)  # $\mathcal L^2_{\rm im} \mathbf K$
    K_im_full = L2_im_K + Sigma                             # $\mathbf K_{\rm im}^{\rm full} = \mathcal L^2_{\rm im} \mathbf K + \sigma_n^2 \mathbf I$
    L = np.linalg.cholesky(K_im_full)                       # Cholesky decomposition to get the inverse of $\mathbf K_{\rm im}^{\rm full}$
    
    # solve for alpha
    alpha = np.linalg.solve(L, Z_exp.imag)
    alpha = np.linalg.solve(L.T, alpha)                     # $(\mathcal L^2_{\rm im} \mathbf K + \sigma_n^2 \mathbf I)^{-1} \mathbf Z^{\rm exp}_{\rm im}$
    return 0.5*np.dot(Z_exp.imag,alpha) + np.sum(np.log(np.diag(L)))


def der_ell_matrix_L2_im_K(xi_vec, sigma_f, ell):

    N_freqs = xi_vec.size
    der_ell_L2_im_K = np.zeros([N_freqs, N_freqs])

    for n in range(0, N_freqs):
        xi = xi_vec[n]
        xi_prime = xi_vec[0]
        integral, tol = integrate.quad(integrand_der_ell_L2_im, -np.inf, np.inf, epsabs=1E-12, epsrel=1E-12, args=(xi, xi_prime, sigma_f, ell))

        np.fill_diagonal(der_ell_L2_im_K[n:, :], exp(xi_prime-xi)*(sigma_f**2)/(ell**3)*integral)
        np.fill_diagonal(der_ell_L2_im_K[:, n:], exp(xi_prime-xi)*(sigma_f**2)/(ell**3)*integral)

    return der_ell_L2_im_K



def grad_NMLL_fct(theta, Z_exp, xi_vec):
    
    sigma_n = theta[0] 
    sigma_f = theta[1]  
    ell = theta[2]
    
    N_freqs = xi_vec.size
    Sigma = (sigma_n**2)*np.eye(N_freqs)
    
    L2_im_K = matrix_L2_im_K(xi_vec, xi_vec, sigma_f, ell)
    K_im_full = L2_im_K + Sigma
    
    L = np.linalg.cholesky(K_im_full)
    # solve for alpha
    alpha = np.linalg.solve(L, Z_exp.imag)
    alpha = np.linalg.solve(L.T, alpha)
    
    # compute inverse of K_im_full
    inv_L = np.linalg.inv(L)
    inv_K_im_full = np.dot(inv_L.T, inv_L)
    
    # derivative matrices
    der_mat_sigma_n = (2.*sigma_n)*np.eye(N_freqs)
    der_mat_sigma_f = (2./sigma_f)*L2_im_K
    der_mat_ell = der_ell_matrix_L2_im_K(xi_vec, sigma_f, ell)
    
    d_K_im_full_d_sigma_n = - 0.5*np.dot(alpha.T, np.dot(der_mat_sigma_n, alpha)) \
        + 0.5*np.trace(np.dot(inv_K_im_full, der_mat_sigma_n))    
        
    d_K_im_full_d_sigma_f = - 0.5*np.dot(alpha.T, np.dot(der_mat_sigma_f, alpha)) \
        + 0.5*np.trace(np.dot(inv_K_im_full, der_mat_sigma_f))
        
    d_K_im_full_d_ell     = - 0.5*np.dot(alpha.T, np.dot(der_mat_ell, alpha)) \
        + 0.5*np.trace(np.dot(inv_K_im_full, der_mat_ell))

    grad = np.array([d_K_im_full_d_sigma_n, d_K_im_full_d_sigma_f, d_K_im_full_d_ell])

    return grad
