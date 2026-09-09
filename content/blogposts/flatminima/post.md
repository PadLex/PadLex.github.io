# Why does the Flat Minima Hypothesis only hold under a fixed learning rate?
The Flat Minima Hypothesis states that models that converge to a flatter basin tend to generalize better to unseen data. However, [TODO: catchy premise]

<!-- When I first learned of it, I wondered if it could be a useful framework for understanding the Muon optimizer. Perhaps it performs so well by implicitly minimizing sharpness. This blog is about why  **{c2}(such a question is fundamentally ill-posed)**, why existing formulations of the hypothesis are underspecified, and why the hypothesis still offers a useful perspective that has ***{c1}(withstood the test of time)***. -->

## The Promise
Generalization is the one thing we can't measure from the training set — we spend data we'd rather train on just to estimate it. The Flat Minima Hypothesis dangles a tantalizing alternative: what if you could predict how well a model generalizes purely from local information, by probing the loss landscape right around the solution? Get that working and you could select models without a validation set, explain why SGD finds solutions that generalize, and even design optimizers that steer towards flatter basins.

The idea goes back to @hochreiter1997flat, who arrived at it from a minimum description length angle: a flat minimum is one where the weights can be specified sloppily — with fewer bits — without hurting the loss. Fewer bits means a simpler model, and simpler models should generalize better. It's Occam's razor dressed up in information theory. Their formulation never caught on, though. It defined flatness through connected boxes of near-constant loss, required Hessian machinery and a bespoke training algorithm to find them, and landed right before neural networks fell out of fashion for a decade.

The hypothesis got its second life when @keskar2017large attached it to a mystery people actually cared about: why do large training batches generalize worse than small ones? Their answer — large batches converge to sharp minima — came with a crucial simplification. Instead of Hochreiter's boxes, they measured sharpness: (approximately) how much the loss can grow in a small neighborhood around the solution. That's a single number you can compute for any trained model, no bespoke training required. Suddenly the hypothesis was testable at scale, and for a while it looked great: comparing some 40 generalization measures head to head, @jiang2020fantastic found sharpness-based ones to be the most predictive of all.

The Flat Minima Hypothesis relies on the intuition that the validation loss landscape can be approximated as a stochastically perturbed version of the training landscape. If a model converges to a wider/flatter basin in the training landscape, it feels intuitive that it would be more likely to stay within that same basin if the validation-loss landscape were slightly shifted.

%%figure:two-valleys%% The intuition, on a toy one-dimensional loss landscape. The validation landscape (dashed) is the training landscape (solid) shifted by a small offset $\epsilon$. Each point is a run that converged into one of the two valleys. Toggle the validation loss on to lift every run to its loss on the shifted landscape; the vertical trace it leaves behind is its generalization gap. Runs in the sharp valley get pushed up its wall, while runs in the flat valley barely move.

Measuring the width of a basin, however, is not so straightforward. We might initially consider nonlocal approaches such as flood filling the basin. However, this does not scale to the parameter space of ML models, both because they tend to scale poorly with dimensionality and because, in overparametrized setting all basins are technically connected anyway. So really, we're not interested in the width of the basin per se, but rather the distance to the closest wall. One way to frame this task is to ask: if we shifted the converged model in some direction by an offset $\epsilon$, how much would the loss grow by? In the limit $\epsilon \to 0$, this is the curvature of the loss along that direction, aka a second derivative. Taking the worst case over all directions gives us the top eigenvalue of the loss's Hessian matrix, which is called the model's sharpness. Flat regions in a wide basin should have low curvature in every direction and, as you approach one of the basin's walls, the sharpness should steadily increase.

For parameters $w_t$, let $H_t := \nabla_w^2 \mathcal{L}(w_t)$ denote the Hessian of the training loss.

**Raw sharpness:** We define raw (Hessian) sharpness as

$$\mathcal{S}_{\text{raw}}(w_t) := \lambda_{\max}(H_t).$$

## Let's Test It
@keskar2017large's formulation of the Flat Minima Hypothesis predicts that ***{c3}(sharpness should correlate with the model's generalization gap)***. Where the generalization gap is simply the difference between training and validation accuracy, and sharpness measures the peak curvature of the loss function — the top Hessian eigenvalue from above.

This seems easy enough to test. We can train a few hundred CNNs on a simple, but realistic, task like CIFAR-10. Lucky for us, Keller Jordan's cifar10-airbench offers just the scaffold we need to train them quickly (I measured about 11s of wall clock per run on a Hopper GPU, and that includes our per-epoch sharpness measurements). Then, after each run, we can simply measure how well the model generalizes, and test if it correlates with landing in a flatter (less sharp) loss region.

%%figure:sharpness-lds%% Raw sharpness vs. generalization gap at epoch 16, trained with a linear-decay (variable) learning rate. Each point is one run; dashed lines are per-optimizer fits, computed excluding outlier runs that fall far from the trend (beyond 3.3 robust standard deviations); excluded runs are drawn without an outline. Click the legend to include or exclude optimizers, and hover a point for that run's details.

Well shoot. Sharpness seems to be completely uncorrelated with generalization. (Also notice how different optimizer tend to converge to regions of different sharpness, that's unexpected)

## Optimizer researchers make some funny assumptions
So what are we doing differently from @keskar2017large?

Well, it turns out that the field of deep learning optimization research makes some unconventional assumptions. Chief among them, @keskar2017large use a small *fixed* learning rate. Learning rate schedulers, which have become ubiquitous in every other corner of the ML community, are conspicuously absent here. This isn't as arbitrary as it sounds: the theory the field leans on, from convergence proofs to the edge-of-stability results we'll get to below, assumes a constant step size [@cohen2021gdeos]. And when the optimizer itself is the object of study, a scheduler is one more confounder to control for.

%%figure:sharpness-fixed%% Raw sharpness vs. generalization gap at epoch 16, trained with a fixed learning rate — the setting studied by @keskar2017large. Use the toggle to compare the two learning-rate schedules.

And in fact, if we fix the learning rate, we see that among samples trained with SGD, sharpness is clearly correlated with a large generalization gap ($r = 0.49$). This matches @keskar2017large's original results.

## Sharpness is Brittle
But wait a second, why do runs trained with Adam or Muon still form distinct clusters? Shouldn't our hypothesis only be about the geometry of the loss landscape near the model? Why would optimizers affect that?

Most neural network architectures have symmetries along which you can re-parametrize the model without affecting its behaviour. Some symmetries, like rescaling between layers, also affect sharpness. If we halve the weights of one ReLU layer and double the weights of the next, the network computes exactly the same function, but the curvature along the halved layer's directions quadruples. @dinh2017sharp pushed this to its conclusion: any minimum can be re-parametrized to be arbitrarily sharp without changing how the model generalizes. In this light, the hypothesis as presented by @keskar2017large is, taken literally, false. Perhaps the clustering we saw then simply shows that SGD, Adam and Muon each have a different bias for parameter scale.

**Adaptive sharpness:** @kwon2021asam have tried to solve by proposing Adaptive Sharpness.

$$\mathcal S_{\text{adapt}}(w) := \max_{\|T_w^{-1}\epsilon\|\le\rho} \big[\mathcal{L}(w+\epsilon)-\mathcal{L}(w)\big],$$

where $T_w$ is a normalization operator depending on the current parameters. This defines a perturbation set in scale-normalized space, making the measure invariant to loss-preserving parameter rescaling.

%%figure:sharpness-adaptive%% Adaptive sharpness vs. generalization gap at epoch 16, trained with a fixed learning rate. This figure exposes the full controls: pick the learning-rate schedule and the sharpness measure on the x-axis, and scrub through training epochs; Reset restores the default view.

This looks much better now! Runs from the different optimizers land on far more similar adaptive sharpness values (the Muons still sit about 2x lower than SGD and Adam) and adaptive sharpness correlates even more strongly with the generalization gap ($r = 0.45$–$0.69$ per optimizer, versus $0.27$–$0.49$ for raw sharpness).

## Questioning the Hypothesis utility / field's assumptions
Why does the hypothesis only hold with a fixed learning rate though?

Part of the answer is boring statistics. Under the linear-decay schedule, every well-tuned run lands in nearly the same place: within each optimizer, the generalization gap has a standard deviation of just 0.002–0.003, compared to 0.007–0.05 with a fixed learning rate. There's almost no variance left for sharpness (or anything else) to predict, so whatever correlation exists gets buried in seed noise.

Edge of stability research suggests a more mechanistic story on top of that. Under a fixed learning rate $\eta$, gradient descent doesn't settle wherever it pleases: sharpness rises until it reaches the stability threshold $2/\eta$, then hovers there [@cohen2021gdeos; @jastrzebski2020breakeven]. A decaying schedule keeps loosening that threshold as $\eta$ shrinks, so the sharpness you measure at the end says more about where the annealing froze the trajectory than about the basin the model landed in. This also matches @andriushchenko2023modern, who ran a much larger study and concluded that sharpness mostly tracks hyperparameters like the learning rate, not generalization itself. I find this story compelling, but I haven't tested it directly.

Or could we just be reading tea leaves? Modern models are so overparametrized that all basins really are connected by low-loss paths. Maybe low sharpness is just a proxy for "this run happened to converge a bit further". That one we can test: if sharpness only reflects convergence, its correlation with the gap should vanish once we account for training accuracy. It doesn't. The fixed-learning-rate correlations survive the partialling, and most come out slightly stronger (Coupled Adam's adaptive sharpness goes from $r = 0.67$ to $0.72$), while the scheduled runs stay uncorrelated. So sharpness does carry information beyond how well the model fit the training set — just, apparently, only under a fixed learning rate. (Ideally we'd control for training loss rather than accuracy, but accuracy is what I logged.)

<!-- ## Could there be any good measure of flatness?
[TODO reconsider the original formulation from @hochreiter1997flat, explain why it's inpractical, talk about what other measures are computable at the scale of modern models] -->

## Bonus: Muon works great!
Our results align with prior work: Muon variants consistently achieve higher validation accuracy. Under LDS, Normalized Muon reaches 0.94 ± 0.002, outperforming SGD and Adam (both 0.92 ± 0.002). In contrast, fixed learning rates degrade performance for all optimizers (e.g., Normalized Muon: 0.94 → 0.90; SGD: 0.92 → 0.80).

Two details stand out. First, Muon is the most robust to losing the scheduler: switching to a fixed learning rate costs Decoupled Muon about 3 points of validation accuracy and Normalized Muon 4, versus 5 for Adam and 12 for SGD — which also becomes wildly seed-dependent (± 0.06). Second, to close the loop on the question that motivated this post: Muon's edge is clearly not explained by flatness. Under LDS, both Muon variants land at *higher* adaptive sharpness than SGD and Adam ([Table 1](#tbl-results)) while delivering the best validation accuracy. If you want a geometric story for Muon, recent work casting it as steepest descent under a spectral norm constraint [@chen2025muonspectralnorm] seems like a better bet than the Flat Minima Hypothesis.


## Implementation Details
All training runs used a fork of Airbench [@jordan2024airbench], an optimized script that trains a VGG-like CNN to 94% accuracy on the CIFAR-10 [@cifar10] image classification dataset.

We only modified the original Airbench script by (i) adding a callback function called after each epoch to measure sharpness, (ii) supporting training with a fixed learning rate in addition to the original Linear Decay Scheduler (LDS), and (iii) implementing DecoupledMuon, CoupledAdam, and CoupledSGD in addition to the NormalizedMuon implementation from the original script.

**A note on optimizer naming:** Vanilla Muon [@jordan2024muon] orthogonalizes each weight matrix's momentum with a Newton-Schulz iteration before applying the update. Decoupled Muon adds decoupled (AdamW-style) weight decay, matching Muon's reference implementation and the variant used to train LLMs at scale [@liu2025muonscalableLLM] — this is the canonical Muon, so our figures show it by default. Normalized Muon is Airbench's speedrun-specific variant [@jordan2024airbench], which additionally rescales each weight matrix to a fixed Frobenius norm before every update; it is hidden by default in the figures above, and clicking its legend chip brings it back. Coupled, by contrast, refers to classical weight decay, where the penalty is added to the gradient as L2 regularization rather than applied directly to the weights: Coupled SGD and Coupled Adam are the textbook SGD and Adam updates.

For each optimizer, we first perform an extensive hyperparameter sweep using Bayesian optimization with a Gaussian-process (GP) surrogate model. We consider both a fixed learning rate and an LDS schedule. Each sweep consists of 128-512 trials where the GP posterior selects hyperparameters to maximize validation accuracy. All reported results are using the best hyperparameters found by this procedure, with one exception: for SGD and Adam under a fixed learning rate we manually lowered the learning rates below the sweep's optimum (SGD: head/bias 0.241/0.058 → 0.01/0.01; Adam: head/bias 0.388/0.437 → 0.08/0.08). [TODO: say why — did the sweep-best fixed LRs diverge?]


For completeness, we report the means and standard deviations of the aforementioned accuracy and sharpness measures in [Table 1](#tbl-results).

%%table:results%%

%%references%%
