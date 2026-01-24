# fabric-pr

The goal of this part is to recover LESSONS LEARNED about the various hardware, software,
and other systems I deal with, with a flow like the following. This is likely
an iterated game, where the first passes help to converge on the set of entities
(software packages and cross-cutting concepts) we want to be annotating, and
then subsequent steady-state iteration is mostly just grooming those descriptions
and keeping them up to date.

Beforehand: summarize the changes in each PR (which may include unrelated changes) as
well as any attached title, bug or comment. This should be a canned set of mcp-cli
calls as well as a fabric-managed prompt. These summaries are themselves entities (albeit small ones) - mostly so the user can respond to requests-for-comment by
marking up the summary with human-provided ansers or clarifications, then iterating.

* FOR EACH software package or concept we're currently tracking (this is in
  the form of a list of README links), read the README and the current state
  of the relevant folder, then review the summarized changes and make a
  list of the changes (both PR and actual description) that are relevant to it.
  Also output a REQUESTS.md document with a bulleted list of information you
  don't have that would be helpful (whether documentation, the configuration of
  neighboring systems, or user intent). The model should limit its imagination
  here and only use clearly inferrable user intent; otherwise ask for the motivation
  or reasoning behind a change.
* review the overall list of annotated changes and propose any packages or concepts
  that seem to be logically missing, and add them to PROPOSALS.md. In particular
  this includes cross-cutting concepts (hypothetically if every new package had
  a couple of false starts getting its parameters plumbed through from Terraform
  to Helm, the changes should be attach to their individual packages, but ALSO we
  should propose a "parameter passing" concept which is missing. Then a future
  iteration would tag those changes to both the relevant software package AND to
  the cross-cutting concept, and we would be in a position to extract a lesson
  learned.)
* review the whole body of package-and-changes docs, identify which
  systems interact or have cross-cutting effects, and annotate the
  interacting partners in their README files.

So far that's just grooming the static knowledge base with connectivity
and interaction information. But then we look at building out the stories:

* For each software system or concept, collect its changes into one or more
  bugs and features, taking advantage of hindsight to understand where an
  initial fix was actually incomplete or confidently wrong, or where a feature
  led to secondary fixes before stabilizing.
* For each of these bugs or features, write a brief but technical summary
  of the set of changes involved. Identify 1-3 lessons learned from each
  of these, including things that worked as advertised, but especially
  anything that was tried and DIDN'T work.
* Enhance the base concepts with links to the bug/feature writeups, and inline
  a brief summary of the lessons learned.

## Tooling notes

Using [fabric](https://github.com/danielmiessler/Fabric) to invoke models
with managed prompts, v0 with "built-in" prompts.

Hmm it looks like <https://github.com/danielmiessler/Fabric/blob/main/cmd/generate_changelog/README.md>
has basically already covered this territory (though perhaps without quite
the focus on "recover the stuff I didn't bother to write down"). But the
interesting part is the follow-up anyway.

mcp-cli looks useful to use other folk's wisdom to encode stuff in friendly
ways (e.g. git changes or code structure) while still feeding a static view
into fabric.
