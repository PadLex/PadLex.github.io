# Questioning the Flat Minima Hypothesis
The Flat Minima Hypothesis states that models that converge to a flatter basin tend to generalize better to unseen data.

[TODO explain why we should care about it. Why did @hochreiter1997flat first pose the hypothesis? The premise that we could infer a model's robustness based soley on local info about the geometry of the loss landscape is worth expanding on. Why did it not catch on untill @keskar2017large? Explain the simplifactions they made to make it usable. Explain what's the exciting promise that keskar2017large make.]

<!-- When I first learned of it, I wondered if it could be a useful framework for understanding the Muon optimizer. Perhaps it performs so well by implicitly minimizing sharpness. This blog is about why  **{c2}(such a question is fundamentally ill-posed)**, why existing formulations of the hypothesis are underspecified, and why the hypothesis still offers a useful perspective that has ***{c1}(withstood the test of time)***. -->

## The Promise
[TODO explain why we should care. Essentially, explain why @hochreiter1997flat was motivated to come up with their formulation. The reason why nobody cared. And then why everyone cared about it after @keskar2017large.]

The Flat Minima Hypothesis relies on the intuition that the validation loss landscape can be approximated as a stochastically perturbed version of the training landscape. If a model converges to a wider/flatter basin in the training landscape, it feels intuitive that it would be more likely to stay within that same basin if the validation-loss landscape were slightly shifted. [TODO: we should add a home made 2D figure to demonstrate this idea: we could have a 2D loss landscape with two valleys and a whole bunch of points converged inside of them, if the validation loss where to shift slightly then it should].

Measuring the width of a basin, however, is not so straightforward. We might initially consider [TODO nonlocal?] approaches such as flood filling the basin. However, this does not scale to the parameter space of ML models, both because they tend to scale poorly with dimensionality and because, in overparametrized setting all basins are technically connected anyway. So really, we're not interested in the width of the basin per se, but rather the distance to the closest wall. One way to frame this task is to ask: if we shifted the converged model along each axis by an offset $\epsilon$, how much would the loss grow by? In the limit $\epsilon \to 0$, we can compute this as the diagonal of the loss's Hessian matrix. Aka the second derivative of the loss / the curvature along each dimension. The maximum-magnitude value in this diagonal is called the model's sharpness. Flat regions in a wide basin should have low curvature in every dimension. Meanwhile, as you approach one of the basin's walls, the sharpness should steadily increase. [TODO is sharpness just looking at the curvature along the bases? If a wall is present in between them but not along any pure axis whoudl sharpness miss it?]

For parameters $w_t$, let $H_t := \nabla_w^2 \mathcal{L}(w_t)$ denote the Hessian of the training loss.

**Raw sharpness:** We define raw (Hessian) sharpness as

$$\mathcal{S}_{\text{raw}}(w_t) := \lambda_{\max}(H_t).$$

## Let's Test It
@keskar2017large's formulation of the Flat Minima Hypothesis predicts that ***{c3}(sharpness should correlate with the model's generalization gap)***. Where the generalization gap is simply the difference between training and validation accuracy, and sharpness measures the peek curvature of the loss function. [TODO often defined as the maximum magnitude value in the diagonal of the Hessian matrix?]

This seems easy enough to test. We can train a few hundred CNNs on a simple, but realistic, task like CIFAR-10. Lucky for us, Keller Jordan's cifar10-airbench offers just the scaffold we need to train them quickly (I measured sub-3s [TODO check time in wandb] per run on a Hopper GPU). Then, after each run, we can simply measure how well the model generalizes, and test if it correlates with landing in a flatter (less sharp) loss region.

%%figure:sharpness-lds%% Raw sharpness vs. generalization gap at epoch 16, trained with a linear-decay (variable) learning rate. Each point is one run; dashed lines are per-optimizer fits, computed excluding outlier runs that fall far from the trend (beyond 2.5 robust standard deviations); excluded runs are drawn without an outline. Click the legend to include or exclude optimizers, and hover a point for that run's details.

Well shoot. Sharpness seems to be completely uncorrelated with generalization. (Also notice how different optimizer tend to converge to regions of different sharpness, that's unexpected)

## Optimizer researchers make some funny assumptions
So what are we doing differently from @keskar2017large?

Well, it turns out that the field of optimization research [TODO is that the most specific field name?] makes some unconventional assumptions. Chief among them, @keskar2017large use a small *fixed* learning rate. Learning rate schedulers, which have become ubiquitous in every other corner of the ML community, are seen as confounding variables when studying optimizers.

%%figure:sharpness-fixed%% Raw sharpness vs. generalization gap at epoch 16, trained with a fixed learning rate — the setting studied by @keskar2017large. Use the toggle to compare the two learning-rate schedules.

And in fact, if we fix the learning rate, we see that among samples trained with SGD, sharpness is very strongly correlated with a large generalization gap. This exactly matches @keskar2017large's original results.

## Sharpness is Brittle
But wait a second, why do runs trained with Adam or Muon still form distinct clusters? Shouldn't our hypothesis only be about the geometry of the loss landscape near the model? Why would optimizers affect that?

Most neural network architectures have symmetries (TODO is that the right word?) along which you can re-parametrize the model without affecting its behaviour. Some symmetries, like scale invariance, also affect sharpness. If we double the magnitude of each weight in a dense neural network, its behaviour will not change, but we've doubled its raw sharpness. In this light, the hypothesis as presented by @keskar2017large is clearly falsifiable (TODO is that word appropriate? Should I just say false?). Perhaps the clustering we saw then simply shows that SGD, Adam and Muon each have a different bias for parameter scale.

**Adaptive sharpness:** @kwon2021asam have tried to solve by proposing Adaptive Sharpness.

$$\mathcal S_{\text{adapt}}(w) := \max_{\|T_w^{-1}\epsilon\|\le\rho} \big[\mathcal{L}(w+\epsilon)-\mathcal{L}(w)\big],$$

where $T_w$ is a normalization operator depending on the current parameters. This defines a perturbation set in scale-normalized space, making the measure invariant to loss-preserving parameter rescaling.

%%figure:sharpness-adaptive%% Adaptive sharpness vs. generalization gap at epoch 16, trained with a fixed learning rate. This figure exposes the full controls: pick the learning-rate schedule and the sharpness measure on the x-axis, and scrub through training epochs; Reset restores the default view.

This looks much better now! Runs from the different optimizers land on similar adaptive sharpness values and adaptive sharpness correlates even mode strongly with the generalization gap.

## Questioning the Hypothesis utility / field's assumptions
Why does the hypothesis only hold with a fixed learning rate though? [TODO could it be that we're just reading tealeaves? Like sure, maybe the hypothesis is correct, but in practive modern models are very overparametrized, thus all basins really are connected by a low-loss bazien path. So really, it's more that if you fully converge that correlates with better generalization? Could I design experiments to prrove or disprove this based on the wandb data alone? Maybe we could treat the final training loss as a confounder as see how strong the correlation between sharpness and generalization is after accounting for it?] 

<!-- ## Could there be any good measure of flatness?
[TODO reconsider the original formulation from @hochreiter1997flat, explain why it's inpractical, talk about what other measures are computable at the scale of modern models] -->

## Bonus: Muon works great!
[TODO briefly discuss Muoan's performance compared the other optimizers]
Our results align with prior work: Muon variants consistently achieve higher validation accuracy. Under LDS, Normalized Muon reaches 0.94 ± 0.002, outperforming SGD and Adam (both 0.92 ± 0.002). In contrast, fixed learning rates degrade performance for all optimizers (e.g., Normalized Muon: 0.94 → 0.90; SGD: 0.92 → 0.80).


## Implementation Details
All training runs used a fork of Airbench [@jordan2024airbench], an optimized script that trains a VGG-like CNN to 94% accuracy on the CIFAR-10 [@cifar10] image classification dataset.

We only modified the original Airbench script by (i) adding a callback function called after each epoch to measure sharpness, (ii) supporting training with a fixed learning rate in addition to the original Linear Decay Scheduler (LDS), and (iii) implementing DecoupledMuon, CoupledAdam, and CoupledSGD in addition to the NormalizedMuon implementation from the original script.

**A note on optimizer naming:** Vanilla Muon [@jordan2024muon] orthogonalizes each weight matrix's momentum with a Newton-Schulz iteration before applying the update. Decoupled Muon adds decoupled (AdamW-style) weight decay, matching Muon's reference implementation and the variant used to train LLMs at scale [@liu2025muonscalableLLM] — this is the canonical Muon, so our figures show it by default. Normalized Muon is Airbench's speedrun-specific variant [@jordan2024airbench], which additionally rescales each weight matrix to a fixed Frobenius norm before every update; it is hidden by default in the figures above, and clicking its legend chip brings it back. Coupled, by contrast, refers to classical weight decay, where the penalty is added to the gradient as L2 regularization rather than applied directly to the weights: Coupled SGD and Coupled Adam are the textbook SGD and Adam updates.

For each optimizer, we first perform an extensive hyperparameter sweep using Bayesian optimization with a Gaussian-process (GP) surrogate model. We consider both a fixed learning rate and an LDS schedule. Each sweep consists of 128-512 trials where the GP posterior selects hyperparameters to maximize validation accuracy. All reported results are using the best hyperparameters found by this procedure.


For completeness, we report the means and standard deviations of the aforementioned accuracy and sharpness measures in [Table 1](#tbl-results).

%%table:results%%

%%references%%
