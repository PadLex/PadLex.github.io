# Questioning the Flat Minima Hypothesis
The Flat Minima Hypothesis states that models that converge to a flatter basin tend to generalize better to unseen data. As we try to empirically verify the hypothesis for ourselves, we'll find that current formulations of it are still incomplete. Yet, the evidence genuinely hints at a powerful connection between the geometry of the loss landscape during training and how a model ends up performing in the real world.

## Intuition
A common intuition for the Flat Minima Hypothesis is that the validation loss landscape can be approximated as a stochastically perturbed version of the training landscape. If a model converges to a wider basin in the training loss, it feels intuitive that it would be more likely to stay within that same basin if the loss landscape were shifted slightly.

%%figure:two-valleys%% The intuition, on a toy one-dimensional loss landscape (after Figure 1 of @keskar2017large). The validation landscape (dashed) is the training landscape (solid) shifted by a small offset. Each point is a run that converged into one of the two valleys. Toggle the validation loss on to lift every run to its loss on the shifted landscape; the vertical trace it leaves behind is its generalization gap. Runs in the sharp valley get pushed up its wall, while runs in the flat valley barely move.

<!-- Editorial note for later: distinguish the sharpness definitions and their purposes.
Keskar discusses Hessian eigenvalues but measures worst-case loss increases in a weight-dependent box (Metric 2.1), with a +1 floor and loss normalization; also evaluates random subspaces. https://arxiv.org/pdf/1609.04836#page=5
Kwon explicitly connects this to adaptive sharpness with an infinity-norm constraint. Exact scale invariance requires the normalization operator to transform appropriately; fixed additive stabilizers generally break exact invariance. https://arxiv.org/pdf/2102.11600#page=3
Dinh's scaling argument also applies to Keskar's full-space metric, but that argument does not establish the same result for the random-subspace metric. https://arxiv.org/pdf/1703.04933#page=7
Cohen uses the largest Hessian eigenvalue to study optimization stability and explicitly disclaims a generalization claim (footnote 2). Frame our experiment as testing whether this standard optimization measure also predicts generalization; revisit the claim that Keskar's formulation is false. https://arxiv.org/pdf/2103.00065#page=2
-->

## Interesting Background
The original formulation of the Flat Minima Hypothesis is often (incorrectly?) credited to a 1997 paper by @hochreiter1997flat (the conference version is from 1994 [@hochreiter1994simplifying]). They proposed a training algorithm which converges to flatter minima and, crucially, argued that flat minima are "fat maxima" of the Bayesian posterior. However, the view that larger minima generalize better actually predates their work. %%startfold%% Bayesians already preferred posterior maxima with more probability mass [@buntine1991bayesian], and @hinton1993keeping had already argued in 1993 that a network whose parameters tolerate more noise is simpler as it can be written down with fewer bits, and simpler models should generalize better [@wallace1968information; @rissanen1978modeling]. Even though the Flat Minima Hypothesis does not have a clear-cut formulation or a single first proponent, we can still broadly decompose it into three statements: (1) some models are simpler than others in the information-theoretic sense, (2) we can measure how simple they are from the geometry of the loss landscape around them, and (3) these simpler models should generalize better.

Initially, the idea didn't catch on; the 1997 paper only drew a handful of citations. The hypothesis only got a second life 20 years later, when @keskar2017large picked it up while trying to explain why small training batches tend to generalize better than large ones. However, before they could make that connection, they had to propose a new definition of flatness. They coined a local measure of curvature called sharpness. Typically, it's defined as the largest eigenvalue of the Hessian matrix of the model's loss. Sometimes in the literature, people use the mean of the eigenvalues rather than their maximum. Intuitively, either measure of curvature will be smaller if the model converges at the center of a wide, flat minimum and larger in a sharp minimum. Using this measure, Keskar et al. empirically found that larger batches converge to sharper minima. They also observed that sharpness is inversely correlated with generalization, and thus argued that the Flat Minima Hypothesis could explain why large batch sizes generalize poorly.
%%endfold%%

## Let's Test It
@keskar2017large's formulation of the Flat Minima Hypothesis predicts that ***{c3}(sharpness should correlate with the model's generalization gap)***. Here, the generalization gap is simply the difference between training and validation accuracy, and sharpness measures the peak curvature of the loss function.

For parameters $w_t$, let $H_t := \nabla_w^2 \mathcal{L}(w_t)$ denote the Hessian of the training loss.

**Raw sharpness:** We define raw (Hessian) sharpness as

$$\mathcal{S}_{\text{raw}}(w_t) := \lambda_{\max}(H_t).$$

**Generalization gap:** We measure the gap in generalization accuracy as

$$\mathcal{G}(w_t) := \mathrm{Acc}_{\mathrm{train}}(w_t) - \mathrm{Acc}_{\mathrm{val}}(w_t).$$

This seems easy enough to test. We can train a few hundred NNs on a simple but realistic task like CIFAR-10. Lucky for us, Keller Jordan's cifar10-airbench [@jordan2024airbench] offers just the scaffold we need to train them quickly. I got about 11 seconds of wall-clock time per run on a Hopper GPU, and that includes (my poorly optimized) sharpness measurements after every epoch. Then, for each run, we can simply measure how well the model generalizes and test whether the gap between training and validation accuracy correlates with landing in a sharper loss region.

%%figure:sharpness-lds%% Raw sharpness vs. generalization gap at epoch 16, trained with a linear-decay (variable) learning rate. Each point is one run; dashed lines are per-optimizer fits, computed excluding outlier runs that fall far from the trend (beyond 3.3 robust standard deviations); excluded runs are drawn without an outline. The plot cycles through all 16 training epochs once it scrolls into view; pause it, or drag the slider, to hold any single epoch. Click the legend to include or exclude optimizers, and hover a point for that run's details.

Well, shoot. At convergence, sharpness seems to be completely uncorrelated with generalization. Also, notice how different optimizers tend to converge to regions of different sharpness. That's unexpected.

## Optimizer researchers make some funny assumptions
So what are we doing differently from @keskar2017large?

People in optimization research often use simplified training setups to reduce confounders. In particular, learning rate schedulers, which have become ubiquitous in every other corner of the ML community, are often avoided. Like us, @keskar2017large report using Adam and training until the loss stops improving (Section 2.2), but they don't mention what learning rate schedule they use. Their accompanying [example code](https://github.com/keskarnitish/large-batch-training/blob/master/plot_parametric_plot.py), however, uses a *fixed* learning rate.

%%figure:sharpness-fixed%% Raw sharpness vs. generalization gap at epoch 16, trained with a fixed learning rate. Use the toggle to compare the two learning-rate schedules.

And in fact, if we fix the learning rate, we see that among samples trained with SGD, sharpness is clearly correlated with a larger generalization gap ($r = 0.49$). This is finally consistent with @keskar2017large's observation that sharper minima tend not to generalize as well.

## Sharpness is Brittle
But wait a second, why do runs trained with Adam or Muon still form distinct clusters? Shouldn't our hypothesis only be about the geometry of the loss landscape near the model? Why would optimizers affect that?

Most neural network architectures have symmetries along which you can reparameterize the model without affecting its behavior. Some symmetries, like rescaling between layers, also affect sharpness. If we halve the weights of one ReLU layer and double the weights of the next, the network computes exactly the same function, but the curvature along the halved layer's directions quadruples. @dinh2017sharp showed that any minimum can be reparameterized to be arbitrarily sharp without changing how the model generalizes. In this light, the hypothesis, as formulated by @keskar2017large, is false.

@kwon2021asam have tried to solve the rescaling problem by proposing adaptive sharpness.

**Adaptive sharpness:** Adaptive sharpness measures the largest increase in training loss within a small ellipsoid around the current weights, whose axes adapt to the weights' scale. When we rescale the weights without changing the network's function, the ellipsoid rescales with them, keeping the measure unchanged.

$$\mathcal S_{\text{adapt}}(w) := \max_{\|T_w^{-1}\epsilon\|_2\le\rho} \big[\mathcal{L}(w+\epsilon)-\mathcal{L}(w)\big],$$

Here, $w$ denotes the current weights, $\mathcal{L}$ is the training loss, and $\epsilon$ is a perturbation to the weights. The radius $\rho$ controls the neighborhood's size, while $T_w$ scales its axes according to the weights. The constraint $\|T_w^{-1}\epsilon\|_2\le\rho$ restricts the perturbation to this ellipsoid.

%%figure:sharpness-adaptive%% Adaptive sharpness vs. generalization gap at epoch 16, trained with a fixed learning rate.

This looks much better now! Runs from the different optimizers have far more similar adaptive sharpness values, and adaptive sharpness correlates even more strongly with the generalization gap than raw sharpness ($r = 0.45$–$0.69$, versus $0.27$–$0.49$). It seems like the clustering we saw eariler largely showed that SGD, Adam, and Muon each have a different scale bias.

## Questioning the Hypothesis
Why does the hypothesis only hold with a fixed learning rate, though?

Within each optimizer, the generalization gap has near-zero variance. It seems like using a learning rate scheduler leads to more consistent (though not better) generalization. So there's no variance to explain, but if that were the whole story, there should also be near-zero variance in the sharpness, which is not the case.

Or could we just be reading tea leaves? Maybe lower sharpness is just a proxy for a model that converged further, and convergence actually causes the gap? We can test this. If we control for training accuracy, the correlations under a fixed learning rate are actually stronger (Adam's adaptive sharpness goes from $r = 0.67$ to $0.72$), while the scheduled runs stay uncorrelated. In fact, sharpness doesn't even correlate strongly with training accuracy (|r| < 0.3 for every optimizer, under either schedule).

I haven't found a satisfying explanation for this. My best guess is an edge-of-stability effect: under a fixed learning rate $\eta$, sharpness rises during training until it hits the stability threshold $2/\eta$ and then oscillates there [@cohen2021gdeos; @jastrzebski2020breakeven], whereas a decaying schedule keeps loosening that threshold, so the final sharpness says more about where the annealing froze the trajectory than about the basin. Whatever the cause, it throws a serious wrench in the hypothesis's predictive power. The learning rate schedule does not change the loss landscape, only where on it a run ends up, so if the hypothesis were complete, it should hold for those endpoints just the same.
More recent work has also brought the hypothesis into question. @andriushchenko2023modern found that sharpness tracks training hyperparameters like the learning rate rather than generalization itself, and in some settings correlates negatively with out-of-distribution error.

## Promise
While it's incomplete, the hypothesis still holds a lot of potential. In our fixed-learning-rate experiments, we were able to say something about a model's generalization gap from the geometry of its training loss landscape alone. That's a powerful connection, even if we haven't worked out all the kinks.

Maybe flatness isn't the right measure in every setting, and there's a more general geometric property that could reliably track generalization across optimizers and learning rate schedules. If you could find it, you might just have a breakthrough on your hands.

<!-- ## What about non-local measures of flatness?
@hochreiter1997flat originally described flat minima as a "large connected region in weight-space where the error remains approximately constant". It's an intuitive idea, but measuring the volume of such a region directly is computationally infeasable as the number of parameters increases. Even in their own training algorithm, they used a first-order local approximation of flatness. Modern models are also  overparameterized, which introduces another complication: nearly all minima you might converge to are actually connected by low-loss paths [@garipov2018loss; @draxler2018essentially]. If all solutions belong to the same connected low-loss region, we should probably stick to local measures of flattness. -->


## Bonus: Muon works great!
Our results align with prior work: Muon variants consistently achieve higher validation accuracy. Under a linear decay schedule (LDS), Normalized Muon reaches 0.94 ± 0.002, outperforming SGD and Adam (both 0.92 ± 0.002). In contrast, fixed learning rates degrade performance for all optimizers (e.g., Normalized Muon: 0.94 → 0.90; SGD: 0.92 → 0.80).

Two details stand out. First, Muon is the most robust to losing the scheduler: switching to a fixed learning rate costs Muon about 3 percentage points of validation accuracy and Normalized Muon 4, versus 5 for Adam and 12 for SGD — which also becomes wildly seed-dependent (± 0.06). Second, to close the loop on the question that motivated this post: Muon's edge is clearly not explained by flatness. Under LDS, both Muon variants land at *higher* adaptive sharpness than SGD and Adam ([Table 1](#tbl-results)) while delivering the best validation accuracy. If you want a geometric story for Muon, recent work casting it as steepest descent under a spectral norm constraint [@chen2025muonspectralnorm] seems like a better bet than the Flat Minima Hypothesis.


## Implementation Details
All training runs used a fork of Airbench [@jordan2024airbench], an optimized script that trains a VGG-like CNN to 94% accuracy on the CIFAR-10 [@cifar10] image classification dataset.

%%startfold%%We only modified the original Airbench script by (i) adding a callback function called after each epoch to measure sharpness, (ii) supporting training with a fixed learning rate in addition to the original linear decay scheduler (LDS), and (iii) implementing DecoupledMuon, CoupledAdam, and CoupledSGD in addition to the NormalizedMuon implementation from the original script.

**A note on optimizer naming:** Vanilla Muon [@jordan2024muon] orthogonalizes each weight matrix's momentum with a Newton-Schulz iteration before applying the update. Decoupled Muon adds decoupled (AdamW-style) weight decay, matching Muon's reference implementation and the variant used to train LLMs at scale [@liu2025muonscalableLLM]. It's the canonical Muon implementation. Normalized Muon is Airbench's speedrun-specific variant [@jordan2024airbench], which rescales each weight matrix to a fixed Frobenius norm before every update.

For each optimizer, we first perform an extensive hyperparameter sweep using Bayesian optimization with a Gaussian-process (GP) surrogate model. We consider both a fixed learning rate and an LDS schedule. Each sweep consists of 128–512 trials in which the GP posterior selects hyperparameters to maximize validation accuracy. All reported results use the best hyperparameters found by this procedure, plus a bit of manual tuning to reduce run-to-run variance without affecting the mean validation accuracy.

For completeness, we report the means and standard deviations of the aforementioned accuracy and sharpness measures in [Table 1](#tbl-results).

%%table:results%%

%%endfold%%

%%references%%


