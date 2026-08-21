# Questioning the Flat Minima Hypothesis
The Flat Minima Hypothesis states that models that converge to a flatter basin tend to generalize better to unseen data. When I first learned of it, I wondered if it could be a useful framework for understanding the Muon optimizer. Perhaps it performs so well by implicitly minimizing sharpness. This blog is about why such a question is **{c2}(fundamentally ill-posed)**, why existing formulations of the hypothesis are underspecified, and why the hypothesis still offers a useful perspective that has ***{c1}(withstood the test of time)***.

## The Promise
[TODO explain why we should care. Essentially, explain why @hochreiter1997flat was motivated to come up with their formualtion. The reason why nobody cared. And then why everyone cared about it after @keskar2017large.]

The Flat Minima Hypothesis relies on the intuition that the validation loss landscape can be approximated as a stochastically perturbed version of the training landscape. If a model converges to a wider/flatter basin during training landscape, it feels intuitive that it would be more likely to stay within that same basin if the validation-loss landscape where slightly shifted. [TODO: we should add a home made 2D figure to demonstrate this idea: we could have a 2D loss landscape with two valleys and a whole bunch of points converged inside of them, if the validation loss where to shift slightly then it should].

## Sharpness
Measuring the width of a basin, however, is not so straight forward. In very high dimension spaces, we might want to consider local aproaches - flood filling the basin won't scale (and in the overparametrized setting, all basins are technically connected anyway). One way to frame this task is to ask: if we shifted the converged model along each axis by an offset \epsilon, how much would the loss grow by? In the limit -> 0, we can compute this as the diagonal of loss's Hessian matrix. Aka the second derivative of the loss / the curvature along each dimension. The maximum magnitude value in this diagonal is called the model's sharpness. Flat regions in a wide basin should have low curvature in every dimension. While, as you approach one of the basin's walls, the sharpness should steadily increase. [TODO is sharpness just looking at the curvature along the bases? If a wall is present in between them but not along any pure axis whoudl sharpness miss it?]

For parameters $w_t$, let $H_t := \nabla_w^2 \mathcal{L}(w_t)$ denote the Hessian of the training loss.

**Raw sharpness:** We define raw (Hessian) sharpness as

$$\mathcal{S}_{\text{raw}}(w_t) := \lambda_{\max}(H_t).$$


## Let's Test It
@keskar2017large formulation of the Flat Minima Hypothesis predicts that ***{c3}(sharpness should correlate with the model's generalization gap)*** — the difference between training and validation accuracy.

This seems easy enough to test. Whe can train a few hundred CNNs on a simple, but realistic, task like CIFAR-10. Lucky for us, KellerJordan's cifar10-airbench offers just the scafold we need to train them quikly (I measured sub-3s [TODO check time in wandb] per run on a Hopper GPU). Then, after each run, we can simply measure how well the model generalizes, and test if it correlates with landing in flater (less sharp) loss region. [TODO: Show all optimizers with Variable LR] Well shoot. Each optimizer seems to be biased toward converging to regions of different sharpness, but sharpness seems to be compleatly uncorrelated with generalization.

## Optimizer researchers make some funny assumptions
So what are we doing differently from @keskar2017large?

Well it turns out that the field of optimization research [TODO is that the most specific field name?] makes some unconventional assumptions. Chief among them, @keskar2017large use a small *fixed* learning rate. Learning rate schedulers, which have become ubiquitous in every other corner of the ML comunity, are seen as confounding varibles when studying optimizers.

[TODO show fixed LR plot and all three optimizers]

And in fact, if we fix the learning rate, we see that among samples trained with SGD, sharpness is very strongly correlated with a large generalization gap. This exactly matches @keskar2017large original results.

## Sharpness is Brittle 
But wait a second, why do runs trained with Adam or Muon still form distinct clusters? Shouldn't our hypothesis only be about the geometry of the loss landscape near the model? Why would optimizers affect that?

Most neural network architectures have symetries (TODO is that the right word?) along which you can re-parametrize the model without affeting its behaviour. Some symmetries, like scale invariance, also affect sharpness. If we double the magnitude of each weight in a dense neural network, its behaviour will not change but we've doubled it's raw sharpness. In this light, the hypothesis as presented by @keskar2017large is clearly falsifiable (TODO is that word appropriate? Should I just say false?). Perhaps the clustering we saw then simply shows that SGD, Adam and Muon each have a different bias for parameter scale.


**Adaptive sharpness:** This is exactly the problem that @kwon2021asam tried to solve when proposing Adaptive Sharpness.

$$\mathcal S_{\text{adapt}}(w) := \max_{\|T_w^{-1}\epsilon\|\le\rho} \big[\mathcal{L}(w+\epsilon)-\mathcal{L}(w)\big],$$

where $T_w$ is a normalization operator depending on the current parameters. This defines a perturbation set in scale-normalized space, making the measure invariant to loss-preserving parameter rescaling.

[TODO show final plot with Adaptive Sharpness]

These results finally match 

## Could there be any good measure of flatness?
[TODO reconsider the original formulation from @hochreiter1997flat, explain why it's inpractical, talk about what other measures are computable at the scale of modern models]

## Questioning the fileld's assumptions
[TODO Does it really make sense for the hypothesis to only apply when we use a fixed learning rate? What could be so different?]

## Implementation Details

We base our first experimental setup on a variant of Airbench [@jordan2024airbench], an optimized script that trains a VGG-like CNN to 94% accuracy on the CIFAR-10 [@cifar10] image classification dataset.

We modify the Airbench script by (i) adding a callback function called after each epoch to measure sharpness, (ii) supporting training with a fixed learning rate in addition to the original Linear Decay Scheduler (LDS), and (iii) implementing DecoupledMuon, CoupledAdam, and CoupledSGD in addition to the NormalizedMuon implementation from the original script.

For each optimizer, we perform an extensive hyperparameter sweep using Bayesian optimization with a Gaussian-process (GP) surrogate model. We consider both a fixed learning rate and an LDS schedule. Each sweep consists of 128-512 trials where the GP posterior selects hyperparameters to maximize validation accuracy. All reported results are using the best hyperparameters found by this procedure.

Starting with highly optimized architectures and hyperparameters lends weight to the empirical observations we make regarding Muon's performance compared to Adam and SGD, and allows us to measure sharpness in a practical setting.

We train each run for 16 epochs to ensure convergence. After the final epoch, we report per-optimizer mean validation accuracy, generalization gap, and both raw and adaptive sharpness. For each optimizer, we compute correlation between the sharpness and the generalization gap.

Turning to performance, our results align with prior work: Muon variants consistently achieve higher validation accuracy. Under LDS, Normalized Muon reaches 0.94 ± 0.002, outperforming SGD and Adam (both 0.92 ± 0.002). In contrast, fixed learning rates degrade performance for all optimizers (e.g., Normalized Muon: 0.94 → 0.90; SGD: 0.92 → 0.80).

For completeness, we report the means and standard deviations of the aforementioned accuracy and sharpness measures in [Table 1](#tbl-results).

%%table:results%%

%%references%%
