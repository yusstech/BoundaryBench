# Candidate ownership checklist (before citing this in a research application)

The first version of this repository was generated with AI assistance. The point
is NOT to present that generated scaffold as your original independent research.
Your contribution is to validate, critique, improve, run, and communicate an
experiment you genuinely understand. Keep the commit history honest.

## Must do, in order

1. **Read `policy.py` yourself.** In writing, explain why untrusted notes cannot
   alter verified authorization, and identify two ways the current gate could fail.
2. **Run unit tests locally** and inspect each of the 16 scenarios; change cases
   you find unrealistic. Commit your edits and explain why you made them.
3. **Add an experiment you designed:** suggested: vary the provenance of retrieved
   notes (signed service event, customer message, unverified internal note), hold
   the user task constant and document a new hypothesis before testing.
4. **Collect real model outputs** using a user-owned API key, pinned model ID,
   at least ten repetitions for each scenario. Capture raw counts and reasons.
5. **Investigate failures:** pick three examples of unexpected model behavior,
   show the trusted task, untrusted note, proposed tool, policy verdict and your
   own analysis of the mechanism.
6. **Write an honest research memo:** question, setup, key measurements, surprising
   failure cases, limitations and next experiments; disclose AI assistance.

## Interview self-check

You should be able to explain, without notes:

- Why a model's stated confidence is not a trusted authorization signal.
- Why this benchmark measures one-step tool proposals, not whole-agent safety.
- What the paired scenario controls isolate, and what remains confounded.
- Why policy-valid malicious replies evade the hard-coded gate.
- What would falsify your preferred hypothesis.
- Which parts you personally implemented, validated, changed and analyzed.

If you cannot yet answer these, the project is not ready to present as evidence
of independent research or senior technical leadership.
