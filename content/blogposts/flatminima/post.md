# Questioning the Flat Minima Hypothesis

The Flat Minima Hypothesis states that models that converge to a flatter basin tend to generalize better to unseen data. When I first learned of it, I wondered if it could be a useful framework for understanding the Muon optimizer. Perhaps it performs so well by implicitly minimizing sharpness. This blog is about why such a question is **{c2}(fundamentally ill-posed)**, why existing formulations of the hypothesis are underspecified, and why the hypothesis still offers a useful perspective that has ***{c1}(withstood the test of time)***.

## Flat Minima Hypothesis

The Flat Minima Hypothesis [@hochreiter1997flat; @keskar2017large] predicts that ***{c3}(sharpness should correlate with the model's generalization gap)*** — the difference between training and validation accuracy. It relies on the intuition that the validation loss landscape can be approximated as a stochastically perturbed version of the training landscape. Subsequent work has highlighted the limitations of this hypothesis. Most notably, Dinh et al. [@dinh2017sharp] demonstrated that raw sharpness is not scale-invariant; one can alter it via re-parametrization without changing the model's function. This occurs frequently when comparing models across different optimizers. In response, methods such as Adaptive Sharpness-Aware Minimization (ASAM) [@kwon2021asam] have been proposed to define a scale-invariant geometric measure of a minimum's size. By validating the Flat Minima Hypothesis for Muon's solutions, we investigate whether there exist sharpness-hacking reparametrizations beyond scale invariance that a novel optimizer like Muon might inadvertently favor.

## Sharpness

For parameters $w_t$, let $H_t := \nabla_w^2 \mathcal{L}(w_t)$ denote the Hessian of the training loss.

**Raw sharpness:** We define raw (Hessian) sharpness as

$$\mathcal{S}_{\text{raw}}(w_t) := \lambda_{\max}(H_t).$$

Raw sharpness suffers from sensitivity to loss-preserving parameter rescaling, which is particularly an issue when comparing sharpness across solutions derived from different optimizers [@kwon2021asam]. Two parameterizations with identical functions can yield arbitrarily different sharpness values.

**Adaptive sharpness:** To avoid conflating optimizer behavior with irrelevant scaling effects, we additionally report adaptive sharpness [@kwon2021asam], defined as

$$\mathcal S_{\text{adapt}}(w) := \max_{\|T_w^{-1}\epsilon\|\le\rho} \big[\mathcal{L}(w+\epsilon)-\mathcal{L}(w)\big],$$

where $T_w$ is a normalization operator depending on the current parameters. This defines a perturbation set in scale-normalized space, making the measure invariant to loss-preserving parameter rescaling. Unlike classical sharpness it should be comparable across different optimizers.

## Generalization Benchmark Methodology

We base our first experimental setup on a variant of Airbench [@jordan2024airbench], an optimized script that trains a VGG-like CNN to 94% accuracy on the CIFAR-10 [@cifar10] image classification dataset.

We modify the Airbench script by (i) adding a callback function called after each epoch to measure sharpness, (ii) supporting training with a fixed learning rate in addition to the original Linear Decay Scheduler (LDS), and (iii) implementing DecoupledMuon, CoupledAdam, and CoupledSGD in addition to the NormalizedMuon implementation from the original script.

For each optimizer, we perform an extensive hyperparameter sweep using Bayesian optimization with a Gaussian-process (GP) surrogate model. We consider both a fixed learning rate and an LDS schedule. Each sweep consists of 128-512 trials where the GP posterior selects hyperparameters to maximize validation accuracy. All reported results are using the best hyperparameters found by this procedure.

Starting with highly optimized architectures and hyperparameters lends weight to the empirical observations we make regarding Muon's performance compared to Adam and SGD, and allows us to measure sharpness in a practical setting.

We train each run for 16 epochs to ensure convergence. After the final epoch, we report per-optimizer mean validation accuracy, generalization gap, and both raw and adaptive sharpness. For each optimizer, we compute correlation between the sharpness and the generalization gap.

%%figure:sharpness%% Per-optimizer correlation of raw/adaptive sharpness with generalization gap. Toggle between the fixed learning rate and the Linear Decay Scheduler (LDS), scrub through training epochs, and click the legend to include or exclude optimizers. Hover a point for that run's details; Reset restores the paper's configuration (fixed LR, epoch 16).

## Generalization Benchmark Results

First, [Figure 1](#fig-sharpness) shows that under a fixed learning rate, ***{c5}(sharpness strongly correlates with generalization gap within each optimizer)***. For raw sharpness, Pearson correlations range from 0.27 (Adam) to 0.49 (SGD), all statistically significant. Using adaptive sharpness further strengthens this relationship, with correlations increasing to 0.45–0.69 across optimizers (all $p<10^{-4}$). However, these trends do not transfer across optimizers: raw sharpness varies substantially between methods without corresponding changes in gap, indicating weak cross-optimizer predictiveness.

Beyond correlations, we observe a new pattern in sharpness magnitude. Under a fixed learning rate, Muon exhibits substantially lower adaptive sharpness (ASAM = 0.82 ± 0.229) than SGD (2.06 ± 0.911) and Adam (1.93 ± 0.626). Interestingly, **{c2}(this trend reverses under LDS)**, where Muon becomes sharper (0.71 ± 0.097) than SGD (0.32 ± 0.072) and Adam (0.56 ± 0.074).

Turning to performance, our results align with prior work: Muon variants consistently achieve higher validation accuracy. Under LDS, Normalized Muon reaches 0.94 ± 0.002, outperforming SGD and Adam (both 0.92 ± 0.002). In contrast, fixed learning rates degrade performance for all optimizers (e.g., Normalized Muon: 0.94 → 0.90; SGD: 0.92 → 0.80).

Finally, despite these differences, the mean generalization gap remains stable across schedulers, staying within 0.04–0.08 for all optimizers.

For completeness, we report the means and standard deviations of the aforementioned accuracy and sharpness measures in [Table 1](#tbl-results). We additionally note that, under a scheduled learning rate, we do not observe the correlation predicted by the Flat Minima Hypothesis; see the LDS setting in [Figure 1](#fig-sharpness).

%%table:results%%

## Discussion

In aggregate, we find that the Flat Minima Hypothesis holds for solutions obtained with Muon to a similar extent as for those obtained with Adam and SGD. The fact that, in [Figure 1](#fig-sharpness), runs across different optimizers remain broadly correlated with generalization suggests that scaling bias largely explains the distinct clustering observed in the Raw Sharpness plot. Nevertheless, the Adaptive Sharpness plot continues to exhibit optimizer-specific clusters. If Adaptive Sharpness fully accounted for all parametrization bias, no such clustering should be expected, as the sharpness measure would depend solely on the generalization gap and noise. Muon’s cluster, for instance, exhibits lower Adaptive Sharpness, yet this does not correspond to a comparably reduced generalization gap. Assuming that the Flat Minima Hypothesis holds for some (as yet unidentified) flatness measure, our results indicate that, while Adaptive Sharpness is effective at mitigating scale-related bias, ***{c4}(it is not a completely parametrization-invariant measure of flatness)***.

%%references%%
