# polisher

Eventually lots of things. Starting with PR re-analysis to make up for my lack of focus.

## Concepts to be groomed

### Physical representation

Physical format is a body of Markdown files with YAML frontmatter, following
Obsidian's pattern because it's a nice UI and frontend. These are currently
embedded in the source as README.md files but may become unwieldy.

Each entity should link to a file with a list of mcp-cli commands that
produce a meaningful context for that entity (for example, its config but
also live state, neighboring systems, or other relations). In the grooming
steps for a given concept, the output of these commands should be provided
along with the actual PR or other material being analysed.

* Somehow we should keep track of which parts came from a human versus an LLM,
  to distinguish user intent from possible compounding hallucinations. Most
  LLM-contributed content should include links to sources (PRs, documents,
  or other concepts).
* The YAML front-matter should be entirely curated by tooling; it can use data
  sources beyond the file itself, but should be replaceable if needed, not a
  source of truth. This helps prevent "rumors" from becoming "fact" without a
  source.

### Grooming and iteration

The general pattern is an iterated game where I run a bunch of incremental tasks
overnight, and they have avenues to both update the collection of entities, or
request more information. Examples include

* [[fabric/pr-mining]] - learn about the system by the changes which have impacted it
* [[fabric/product research]] - the underlying open source or commercial product, if any
* Grooming the README itself - should have user intent, along with brief highlights from the PRs, the product research. Links to just about everything.
* Feedback loop (human involved): generating new initial records for concepts discovered during processing.
* Feedback loop (human involved): improving prompts or human-contributed portions
  of documentation in response to REQUESTS
