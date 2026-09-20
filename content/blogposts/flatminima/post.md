# Questioning the Flat Minima Hypothesis
The Flat Minima Hypothesis states that models that converge to a flatter basin tend to generalize better to unseen data. It's a powerful idea. Perhaps it's a useful framework for understanding why the Muon optimizer works so well. Does it implicitly favor flatter minima? As we answer this question and try to empirically verify the hypothesis for ourselves, you'll find a more complicated (and more interesting) story than one might expect.

<!-- [TODO: catchy premise]. Why does the Flat Minima Hypothesis only hold under a fixed learning rate? -->

<!-- When I first learned of it, I wondered if it could be a useful framework for understanding the Muon optimizer. Perhaps it performs so well by implicitly minimizing sharpness. This blog is about why  **{c2}(such a question is fundamentally ill-posed)**, why existing formulations of the hypothesis are underspecified, and why the hypothesis still offers a useful perspective that has ***{c1}(withstood the test of time)***. -->

## Intuition
A common intuition for the Flat Minima Hypothesis is that the validation loss landscape can be approximated as a stochastically perturbed version of the training landscape. If a model converges to a wider basin in the training landscape, it feels intuitive that it would be more likely to stay within that same basin if the validation-loss landscape were slightly shifted.

%%figure:two-valleys%% The intuition, on a toy one-dimensional loss landscape (after Figure 1 of @keskar2017large). The validation landscape (dashed) is the training landscape (solid) shifted by a small offset $\epsilon$. Each point is a run that converged into one of the two valleys. Toggle the validation loss on to lift every run to its loss on the shifted landscape; the vertical trace it leaves behind is its generalization gap. Runs in the sharp valley get pushed up its wall, while runs in the flat valley barely move.

## Interesting Background
The original formulation of the Flat Minima Hypothesis is often (incorrectly?) credited to a 1997 paper by @hochreiter1997flat (the conference version is from 1994 [@hochreiter1994simplifying]). They proposed a training algorithm which converges to flatter minima and, crucially, argued that flat minima are "fat maxima" of the Bayesian posterior. However, the view that larger minima generalize better actually predates their work. %%startfold%% Bayesians already preferred posterior maxima with more probability mass [@buntine1991bayesian], and @hinton1993keeping had already argued in 1993 that a network whose parameters tolerate more noise is simpler as it can be written down with fewer bits, and simpler models should generalize better [@wallace1968information; @rissanen1978modeling]. Even though the Flat Minima Hypothesis does not have a clear-cut formulation or a single first proponent, we can still broadly decompose it into three statements: (1) some models are simpler than others in the information-theoretic sense, (2) we can measure how simple they are from the geometry of the loss landscape around them, and (3) these simpler models should generalize better.

Initially, the idea didn't catch on; the 1997 paper only drew a handful of citations a year for two decades. This was in large part because Hochreiter and Schmidhuber put forward a training algorithm rather than a measure. They based it on a non-local definition of wide minima as a "large connected region in weight-space where the error remains approximately constant". While intuitive, this definition is computationally intractable and fundamentally ill-posed for modern models, where, due to overparameterization, all the minima you converge to tend to be connected by low-loss paths [@garipov2018loss; @draxler2018essentially].

The hypothesis only got a second life 20 years later, when @keskar2017large picked it up (crediting @hochreiter1997flat) while trying to explain why small training batches tend to generalize better than large ones. However, before they could make that connection, they had to propose a new definition of flatness. They coined a local measure of curvature called sharpness. Typically, it's defined as the largest eigenvalue of the Hessian matrix of the model's loss. Sometimes in the literature, people use the mean of the eigenvalues rather than their maximum. Intuitively, either measure of curvature will be smaller if the model converges at the center of a wide, flat minimum and larger in a sharp minimum. Using this measure, Keskar et al. empirically found that larger batches converge to sharper minima. They also observed that sharpness is inversely correlated with generalization, and thus argued that the Flat Minima Hypothesis could explain why large batch sizes generalize poorly.
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

@kwon2021asam have tried to solve the rescaling problem by proposing adaptive sharpness. It's alternative measure of sharpness that is invariant to the parameters' scale.

**Adaptive sharpness:** [TODO insert rigoroulsy correct intuitive explenation for what adpetive sharpenss computes and why that would be scale invariant.]

$$\mathcal S_{\text{adapt}}(w) := \max_{\|T_w^{-1}\epsilon\|\le\rho} \big[\mathcal{L}(w+\epsilon)-\mathcal{L}(w)\big],$$

where $T_w$ is a normalization operator depending on the current parameters. This defines a perturbation set in scale-normalized space, making the measure invariant to loss-preserving parameter rescaling.

%%figure:sharpness-adaptive%% Adaptive sharpness vs. generalization gap at epoch 16, trained with a fixed learning rate.

This looks much better now! Runs from the different optimizers have far more similar adaptive sharpness values, and adaptive sharpness correlates even more strongly with the generalization gap than raw sharpness ($r = 0.45$–$0.69$, versus $0.27$–$0.49$). It seems like the clustering we saw eariler simply showed that SGD, Adam, and Muon each have a different bias toward parameter scale.

## Questioning the Hypothesis
Why does the hypothesis only hold with a fixed learning rate, though?

Within each optimizer, the generalization gap has near-zero variance. It seems like using a learning rate scheduler leads to more consistent (though not better) generalization. So there's no variance to explain, but if that were the whole story, there should also be near-zero variance in the sharpness, which is not the case.

Or could we just be reading tea leaves? Maybe lower sharpness is just a proxy for a model that converged further, and convergence actually causes the gap? We can test this. If we control for training accuracy, the correlations under a fixed learning rate are actually stronger (Coupled Adam's adaptive sharpness goes from $r = 0.67$ to $0.72$), while the scheduled runs stay uncorrelated. In fact, sharpness doesn't even correlate strongly with training accuracy (|r| < 0.3 for every optimizer, under either schedule).

I haven't found a satisfying explanation for this. My best guess is an edge-of-stability effect: under a fixed learning rate $\eta$, sharpness rises during training until it hits the stability threshold $2/\eta$ and then oscillates there [@cohen2021gdeos; @jastrzebski2020breakeven], whereas a decaying schedule keeps loosening that threshold, so the final sharpness says more about where the annealing froze the trajectory than about the basin. Whatever the cause, it throws a serious wrench in the hypothesis's predictive power. The learning rate schedule does not change the loss landscape, only where on it a run ends up, so if the hypothesis were complete, it should hold for those endpoints just the same.
More recent work has also brought the hypothesis into question. @andriushchenko2023modern found that sharpness tracks training hyperparameters like the learning rate rather than generalization itself, and in some settings correlates negatively with out-of-distribution error.

## Promise
[TODO: While it's not complete, the hypothesis clearly holds a lot of potential! In the fixed-learning-rate experiment, we're able to say something about how well a model would generalize to validation data based on the geometry of the training loss landscape alone! That's very powerful if someone can work out the kinks. Maybe flatness isn't it in all cases, and there's some more general geometric variable that could robustly track generalization in all cases? If you could find it, you might just have a breakthrough on your hands.]

<!-- ## Could there be any good measure of flatness?
[TODO reconsider the original formulation from @hochreiter1997flat, explain why it's impractical, talk about what other measures are computable at the scale of modern models] -->

## Bonus: Muon works great!
Our results align with prior work: Muon variants consistently achieve higher validation accuracy. Under a linear decay schedule (LDS), Normalized Muon reaches 0.94 ± 0.002, outperforming SGD and Adam (both 0.92 ± 0.002). In contrast, fixed learning rates degrade performance for all optimizers (e.g., Normalized Muon: 0.94 → 0.90; SGD: 0.92 → 0.80).

Two details stand out. First, Muon is the most robust to losing the scheduler: switching to a fixed learning rate costs Decoupled Muon about 3 percentage points of validation accuracy and Normalized Muon 4, versus 5 for Adam and 12 for SGD — which also becomes wildly seed-dependent (± 0.06). Second, to close the loop on the question that motivated this post: Muon's edge is clearly not explained by flatness. Under LDS, both Muon variants land at *higher* adaptive sharpness than SGD and Adam ([Table 1](#tbl-results)) while delivering the best validation accuracy. If you want a geometric story for Muon, recent work casting it as steepest descent under a spectral norm constraint [@chen2025muonspectralnorm] seems like a better bet than the Flat Minima Hypothesis.


## Implementation Details
All training runs used a fork of Airbench [@jordan2024airbench], an optimized script that trains a VGG-like CNN to 94% accuracy on the CIFAR-10 [@cifar10] image classification dataset.

%%startfold%%We only modified the original Airbench script by (i) adding a callback function called after each epoch to measure sharpness, (ii) supporting training with a fixed learning rate in addition to the original linear decay scheduler (LDS), and (iii) implementing DecoupledMuon, CoupledAdam, and CoupledSGD in addition to the NormalizedMuon implementation from the original script.

**A note on optimizer naming:** Vanilla Muon [@jordan2024muon] orthogonalizes each weight matrix's momentum with a Newton-Schulz iteration before applying the update. Decoupled Muon adds decoupled (AdamW-style) weight decay, matching Muon's reference implementation and the variant used to train LLMs at scale [@liu2025muonscalableLLM] — this is the canonical Muon, so our figures show it by default. Normalized Muon is Airbench's speedrun-specific variant [@jordan2024airbench], which additionally rescales each weight matrix to a fixed Frobenius norm before every update; it is hidden by default in the figures above, and clicking its legend chip brings it back. Coupled, by contrast, refers to classical weight decay, where the penalty is added to the gradient as L2 regularization rather than applied directly to the weights: Coupled SGD and Coupled Adam are the textbook SGD and Adam updates.

For each optimizer, we first perform an extensive hyperparameter sweep using Bayesian optimization with a Gaussian-process (GP) surrogate model. We consider both a fixed learning rate and an LDS schedule. Each sweep consists of 128–512 trials in which the GP posterior selects hyperparameters to maximize validation accuracy. All reported results use the best hyperparameters found by this procedure, plus a bit of manual tuning to reduce run-to-run variance without affecting the mean validation accuracy.

For completeness, we report the means and standard deviations of the aforementioned accuracy and sharpness measures in [Table 1](#tbl-results).

%%table:results%%

%%endfold%%

%%references%%


