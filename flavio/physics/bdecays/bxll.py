r"""Functions for inclusive $B\to X_q\ell^+\ell^-$ decays.

See arXiv:1503.04849."""

import flavio
import numpy as np
from math import pi, log, sqrt
from flavio.math.functions import li2
from flavio.classes import Observable, Prediction
import warnings
from .bxll_qed import wem

def bxll_parameters(par, lep):
    # return lepton and b mass and alpha_s,e at the appropriate scale
    ml = par['m_'+lep]
    scale = flavio.config['renormalization scale']['bxll']
    mb = flavio.physics.running.running.get_mb_pole(par)
    alpha = flavio.physics.running.running.get_alpha(par, scale)
    alpha_s = alpha['alpha_s']
    alpha_e = alpha['alpha_e']
    return ml, mb, alpha_s, alpha_e

def bxll_br_prefactor(par, q, lep):
    # prefactor for the branching ratio normalized to B->X_c enu
    ml, mb, alpha_s, alpha_e = bxll_parameters(par, lep)
    bq = 'b' + q
    xi_t = flavio.physics.ckm.xi('t',bq)(par)
    Vcb = flavio.physics.ckm.get_ckm(par)[1,2]
    C = par['C_BXlnu']
    BRSL = par['BR(B->Xcenu)_exp']
    return alpha_e**2/4./pi**2 / mb**2 * BRSL/C * abs(xi_t)**2/abs(Vcb)**2

def inclusive_wc(q2, wc_obj, par, q, lep, mb):
    r"""Returns a dictionary of "inclusive" Wilson coefficients (including
    SM contributions) where universal bremsstrahlung and virtual corrections
    have been absorbed, as well as the dictionary with the Wilson
    coefficients without these corrections."""
    scale = flavio.config['renormalization scale']['bxll']
    alphas = flavio.physics.running.running.get_alpha(par, scale)['alpha_s']
    # the "usual" WCs
    wc = flavio.physics.bdecays.wilsoncoefficients.wctot_dict(wc_obj, 'b' + q + lep + lep, scale, par, nf_out=5)
    xi_u = flavio.physics.ckm.xi('u','b'+q)(par)
    xi_t = flavio.physics.ckm.xi('t','b'+q)(par)
    # virtual corrections
    Yq2 =flavio.physics.bdecays. matrixelements.Y(q2, wc, par, scale, 'b'+q) + (xi_u/xi_t)*flavio.physics.bdecays.matrixelements.Yu(q2, wc, par, scale, 'b'+q)
    delta_C7 = flavio.physics.bdecays.matrixelements.delta_C7(par=par, wc=wc, q2=q2, scale=scale, qiqj='b'+q)
    delta_C9 = flavio.physics.bdecays.matrixelements.delta_C9(par=par, wc=wc, q2=q2, scale=scale, qiqj='b'+q)
    mb_MSbar = flavio.physics.running.running.get_mb(par, scale)
    ll = lep + lep
    wc_eff = {}
    # add the universal bremsstrahlung corrections to the effective WCs
    brems_7 = 1 + alphas/pi * sigma7(q2/mb**2, scale, mb)
    brems_9 = 1 + alphas/pi * sigma9(q2/mb**2)
    wc_eff['7']  = wc['C7eff_b'+q]  * brems_7      + delta_C7
    wc_eff['7p'] = wc['C7effp_b'+q] * brems_7
    wc_eff['v']  = wc['C9_b'+q+ll]  * brems_9      + delta_C9 + Yq2
    wc_eff['vp'] = wc['C9p_b'+q+ll] * brems_9
    wc_eff['a']  = wc['C10_b'+q+ll] * brems_9
    wc_eff['ap'] = wc['C10p_b'+q+ll]* brems_9
    wc_eff['s']  = mb_MSbar * wc['CS_b'+q+ll]
    wc_eff['sp'] = mb_MSbar * wc['CSp_b'+q+ll]
    wc_eff['p']  = mb_MSbar * wc['CP_b'+q+ll]
    wc_eff['pp'] = mb_MSbar * wc['CPp_b'+q+ll]
    wc_eff['t']  = 0
    wc_eff['tp'] = 0
    return {'wc_eff': wc_eff, 'wc': wc}

def _bxll_dbrdq2(q2, wc_obj, par, q, lep, include_qed=True, include_pc=True):
    # see below: bxll_dbrdq2()
    ml, mb, alpha_s, alpha_e = bxll_parameters(par, lep)
    if q2 < 4*ml**2 or q2 > mb**2:
        return 0
    N = bxll_br_prefactor(par, q, lep)
    wc_dict = inclusive_wc(q2, wc_obj, par, q, lep, mb)
    wc_eff = wc_dict['wc_eff']
    wc = wc_dict['wc']
    sh = q2/mb**2
    mlh = ml/mb
    # LO contributions + bremsstrahlung
    Phi_ll  = f_ll(sh, mlh, alpha_s, wc_eff['7'], wc_eff['v'], wc_eff['a'], wc_eff['s'], wc_eff['p'])
    # for ms=0, rate is simply the sum of C_i and C_i' contributions
    Phi_ll += f_ll(sh, mlh, alpha_s, wc_eff['7p'], wc_eff['vp'], wc_eff['ap'], wc_eff['sp'], wc_eff['pp'])
    if include_qed:
        # log-enhanced QED corrections: BR ~ H_L + H_T
        Phi_ll += Phill_logqed('BR', sh, mb, ml, alpha_s, alpha_e, wc, q, lep)
    if include_pc:
        # 1/mb^2 power correction: BR ~ H_L + H_T
        Phi_ll += Phill_pc_mb2('L', sh, par['lambda_1'], par['lambda_2'], mb, wc, q, lep)
        Phi_ll += Phill_pc_mb2('T', sh, par['lambda_1'], par['lambda_2'], mb, wc, q, lep)
    # denominator of the normalisation to the B->X_u lnu rate
    Phi_u = f_u(alpha_e, alpha_s, par['alpha_s'], mb, par['lambda_1'], par['lambda_2'])
    # fudge factor to account for remaining uncertainty
    if q2 < 12:
        unc = 1 + par['delta_BX'+q+'ll low']
    else:
        unc = 1 + par['delta_BX'+q+'ll high']
    return N * Phi_ll / Phi_u * unc

def bxll_dbrdq2(q2, wc_obj, par, q, lep):
    r"""Inclusive $B\to  X_q\ell^+\ell^-$ differential branching ratio
    normalized to $B\to X_c\ell\nu$ taken from experiment."""
    if q2 > 8 and q2 < 14:
        warnings.warn("The predictions in the region of narrow charmonium resonances are not meaningful")
    if lep == 'l':
        # average of e and mu!
        return (_bxll_dbrdq2(q2, wc_obj, par, q, 'e') + _bxll_dbrdq2(q2, wc_obj, par, q, 'mu'))/2.
    else:
        return _bxll_dbrdq2(q2, wc_obj, par, q, lep)

def f_ll(sh, mlh, alpha_s, C7t, C9t, C10t, CS, CP):
    # The function of Wilson coefficients and kinematical quantities entering
    # the inclusive $B\to Xll$ rate.
    # NB: CS and CP are defined to be dimensionless!
    return (1-sh)**2 * sqrt(1-4*mlh**2/sh) * (
        # SM-like terms for m_l->0: here we add non-univ. bremsstrahlung corrections
        4*abs(C7t)**2*(1+2/sh) * (1+2*mlh**2/sh) * (1 + alpha_s/pi * tau77(sh))
        + 12*(C7t*C9t.conjugate()).real * (1+2*mlh**2/sh) * (1 + alpha_s/pi * tau79(sh))
        + (abs(C9t)**2 + abs(C10t)**2) * (1 + 2*sh + 2*mlh**2*(1-sh)/sh) * (1 + alpha_s/pi * tau99(sh))
        # scalar/pseudoscalar operators
        + 3/2. * sh * ((1-4*mlh**2/sh) * abs(CS)**2 + abs(CP)**2)
        # O(m_l) terms
        + 6*mlh**2 * (abs(C9t)**2 - abs(C10t)**2)
        + 6 * mlh * (CP * C10t.conjugate()).real )

# Functions needed for bremsstrahlung corrections to rate
def sigma9(s):
    return sigma(s) + 3/2
def sigma7(s, scale, mb):
    return sigma(s) + 1/6 - 8/3 * log(scale/mb)
def sigma(s):
    return - 4/3 * li2(s) - 2/3 * log(s) * log(1-s) -2/9 * pi**2 -log(1-s)-2/9 * (1-s) * log(1-s)
def tau77(s):
    return - 2/(9 * (2+s)) * (2 * (1-s)**2 * log(1-s) +(6 * s * (2-2 * s-s**2))/((1-s)**2) * log(s) +(11-7 * s-10 * s**2)/(1-s) )
def tau99(s):
    return -4/(9 * (1+2 * s)) * (2 * (1-s)**2 * log(1-s) +(3 * s * (1+s) * (1-2 * s))/((1-s)**2) * log(s)+(3 * (1-3 * s**2))/(1-s) )
def tau79(s):
    return - (4 * (1-s)**2)/(9 * s) * log(1-s)-(4 * s * (3-2 * s))/(9 * (1-s)**2) * log(s) -(2 * (5-3 * s))/(9 * (1-s))

def Phill_pc_mb2(I, sh, l1, l2, mb, wc, q, lep):
    # 1/mb^2 power correction to Phi_ll
    bq = 'b'+q
    bqll = bq + lep + lep
    coeffs = ['C1_'+bq, 'C2_'+bq, 'C3_'+bq, 'C4_'+bq, 'C5_'+bq, 'C6_'+bq, 'C7eff_'+bq, 'C8eff_'+bq, 'C9_'+bqll, 'C10_'+bqll]
    wc1_10 = np.array([0] + [wc[name] for name in coeffs]) # first entry 0 to shift index by 1
    chi1 = np.zeros((11, 11))
    chi2 = np.zeros((11, 11))
    if I == 'T':
        chi1[7, 7] = 4/(3*sh) * (1-sh) * (5 * sh+3)
        chi1[7, 9] = 4 * (1-sh)**2
        chi1[9, 9] = -sh/3 * (1-sh) * (3 * sh+5)
        chi2[7, 7] = 4/sh * (3 * sh**2+2 * sh-9)
        chi2[7, 9] = 4 * (9 * sh**2-6 * sh-7)
        chi2[9, 9] = sh * (15 * sh**2-14 * sh-5)
    elif I == 'L':
        chi1[7, 7] = 2/3 * (sh-1) * (3 * sh+13)
        chi1[7, 9] = 2 * (1-sh)**2
        chi1[9, 9] = 1/6 * (1-sh) * (13 * sh+3)
        chi2[7, 7] = 2 * (15 * sh**2-6 * sh-13)
        chi2[7, 9] = 2 * (3 * sh**2-6 * sh-1)
        chi2[9, 9] = 1/2 * (-17 * sh**2+10 * sh+3)
    elif I == 'A':
        chi1[7, 10] = -4/3 * (3 * sh**2+2 * sh+3)
        chi1[9, 10] = -2/3 * sh * (3 * sh**2+2 * sh+3)
        chi2[7, 10] = -4 * (9 * sh**2-10 * sh-7)
        chi2[9, 10] = -2 * sh * (15 * sh**2-14 * sh-9)
    else:
        raise ValueError("I should be 'T', 'L', or 'A'")
    return ( l1/mb**2 * np.dot(wc1_10, np.dot(chi1, wc1_10.conj()))
           + l2/mb**2 * np.dot(wc1_10, np.dot(chi2, wc1_10.conj())) ).real

def Phill_logqed(I, sh, mb, ml, alpha_s, alpha_e, wc, q, lep):
    # log-enhanced QED corrections to Phi_ll
    bq = 'b'+q
    bqll = bq + lep + lep
    ast = alpha_s/(4*pi)
    k = alpha_e/alpha_s
    coeffs = ['C1_'+bq, 'C2_'+bq, 'C3_'+bq, 'C4_'+bq, 'C5_'+bq, 'C6_'+bq, 'C7eff_'+bq, 'C8eff_'+bq, 'C9_'+bqll, 'C10_'+bqll]
    wc1_10 = np.array([0] + [wc[name] for name in coeffs]) # first entry 0 to shift index by 1
    scale = flavio.config['renormalization scale']['bxll']
    # (4.19) of 1503.04849
    e = np.zeros((11, 11)) # from 0 to 10
    if I == 'T' or I == 'L' or I == 'BR':
        e[7,7] = 8 * ast**3 * k**3 * sigmaij_I(I, 7, 7, sh)*wem(I, 7, 7, sh, mb, ml, scale)
        e[7,9] = 8 * ast**2 * k**2 * sigmaij_I(I, 7, 9, sh)*wem(I, 7, 9, sh, mb, ml, scale)
        e[9,9] = 8 * ast    * k    * sigmaij_I(I, 9, 9, sh)*wem(I, 9, 9, sh, mb, ml, scale)
        e[2,9] = 8 * ast**2 * k**2 * sigmaij_I(I, 9, 9, sh)*wem(I, 2, 9, sh, mb, ml, scale)
        e[2,2] = 8 * ast**3 * k**3 * sigmaij_I(I, 9, 9, sh)*wem(I, 2, 2, sh, mb, ml, scale)
        e[1,1] = 16/9. * e[2,2]
        e[10,10] = e[9,9]
        e[1,2] = 8/3. * e[2,2]
        e[1,7] = 4/3. * e[2,7]
        e[1,9] = 4/3. * e[2,9]
        e[2,7] = 8 * ast**3 * k**3 * sigmaij_I(I, 7, 9, sh)*wem(I, 2, 7, sh, mb, ml, scale)
    elif I == 'A':
        e[7,10] = 8 * ast**2 * k**2 * sigmaij_I(I, 7, 10, sh)*wem(I, 7, 10, sh, mb, ml, scale)
        e[9,10] = 8 * ast    * k    * sigmaij_I(I, 9, 10, sh)*wem(I, 9, 10, sh, mb, ml, scale)
        e[2,10] = 8 * ast**2 * k**2 * sigmaij_I(I, 9, 10, sh)*wem(I, 2, 10, sh, mb, ml, scale)
        e[1,10] = 4/3. *  e[2,10]
    else:
        raise ValueError("I should be 'T', 'L', 'BR', or 'A'")
    return np.dot(wc1_10, np.dot(e, wc1_10.conj())).real

# kinematical prefactors
def sigma77_T(sh):
    return 8*(1-sh)**2/sh
def sigma79_T(sh):
    return 8*(1-sh)**2
def sigma99_T(sh):
    return 2*sh*(1-sh)**2
def sigma77_L(sh):
    return 4*(1-sh)**2
def sigma79_L(sh):
    return 4*(1-sh)**2
def sigma99_L(sh):
    return (1-sh)**2
def sigma710_A(sh):
    return -8*(1-sh)**2
def sigma910_A(sh):
    return -4*sh*(1-sh)**2
def sigmaij_I(I, i, j, sh):
    if I=='T' and i==7 and j==7:
        return sigma77_T(sh)
    elif I=='T' and i==7 and j==9:
        return sigma79_T(sh)
    elif I=='T' and i==9 and j==9:
        return sigma99_T(sh)
    elif I=='L' and i==7 and j==7:
        return sigma77_L(sh)
    elif I=='L' and i==7 and j==9:
        return sigma79_L(sh)
    elif I=='L' and i==9 and j==9:
        return sigma99_L(sh)
    elif I=='BR' and i==7 and j==7:
        return sigma77_L(sh) +  sigma77_T(sh)
    elif I=='BR' and i==7 and j==9:
        return sigma79_L(sh) + sigma79_T(sh)
    elif I=='BR' and i==9 and j==9:
        return sigma99_L(sh) + sigma99_T(sh)
    elif I=='A' and i==7 and j==7:
        return sigma77_A(sh)
    elif I=='A' and i==7 and j==9:
        return sigma79_A(sh)
    elif I=='A' and i==9 and j==9:
        return sigma99_A(sh)

def f_u(alpha_e, alpha_s, alpha_s_mu0, mb, l1, l2):
    # semileptonic phase space factor for B->Xulnu
    # see (4.8) of 1503.04849
    # NB the O(\tilde alpha_s^2) term is omitted on purpose as including it
    # would mean including terms of O(\tilde \alpha_s^4) in the dominant
    # contribution to the branching ratio, as C9 and C10 are formally of
    # O(\tilde \alpha_s \kappa). This is a numerically relevant choice (around
    # 15% change of the low-q^2 BR).
    ast = alpha_s/4./pi
    k = alpha_e/alpha_s
    eta = alpha_s_mu0/alpha_s
    scale = flavio.config['renormalization scale']['bxll']
    phi1 = (50/3. - 8*pi**2/3.)
    return ( 1 + ast * phi1 + k*(12/23.*(1-1/eta))
               + l1/(2*mb**2) - 9*l2/(2*mb**2))

# functions for observables

def bxll_br_int(q2min, q2max, wc_obj, par, q, lep):
    def obs(q2):
        return bxll_dbrdq2(q2, wc_obj, par, q, lep)
    return flavio.math.integrate.nintegrate(obs, q2min, q2max)

def bxll_br_int_func(q, lep):
    def fct(wc_obj, par, q2min, q2max):
        return bxll_br_int(q2min, q2max, wc_obj, par, q, lep)
    return fct

def bxll_dbrdq2_func(q, lep):
    def fct(wc_obj, par, q2):
        return bxll_dbrdq2(q2, wc_obj, par, q, lep)
    return fct

# Observable instances

_tex = {'e': 'e', 'mu': '\mu', 'tau': r'\tau', 'l': r'\ell'}
for l in ['e', 'mu', 'tau', 'l']:
    for q in ['s', 'd']:

        _process_tex =  r"B\to X_" + q +_tex[l]+r"^+"+_tex[l]+r"^-"
        _process_taxonomy = r'Process :: $b$ hadron decays :: FCNC decays :: $B\to X\ell^+\ell^-$ :: $' + _process_tex + r"$"

        # binned branching ratio
        _obs_name = "<BR>(B->X"+q+l+l+")"
        _obs = Observable(name=_obs_name, arguments=['q2min', 'q2max'])
        _obs.set_description(r"Binned branching ratio of $" + _process_tex + r"$")
        _obs.tex = r"$\langle \text{BR} \rangle(" + _process_tex + r")$"
        _obs.add_taxonomy(_process_taxonomy)
        Prediction(_obs_name, bxll_br_int_func(q, l))

        # differential branching ratio
        _obs_name = "dBR/dq2(B->X"+q+l+l+")"
        _obs = Observable(name=_obs_name, arguments=['q2'])
        _obs.set_description(r"Differential branching ratio of $" + _process_tex + r"$")
        _obs.tex = r"$\frac{d\text{BR}}{dq^2}(" + _process_tex + r")$"
        _obs.add_taxonomy(_process_taxonomy)
        Prediction(_obs_name, bxll_dbrdq2_func(q, l))
