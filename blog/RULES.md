# Blog rules

Injected into every drafting and editing prompt. Edit this file to tune style - no code
changes needed. Hard rules marked [enforced] are also validated in code
(backend/app/publish/blog_export.py:validate_post) and will block a draft.

## Hard rules [enforced]

- Frontmatter required: date (YYYY-MM-DD), published (false on creation), tags, slug
  (kebab-case), sources (vault-relative paths)
- No unresolved [[wikilinks]] - resolve to plain text, or a /slug link if the target is a
  published post
- Never use notes marked `private: true` or anything under Memory/ as sources
- Hyphens only - no em or en dashes
- Every code fence carries a language tag
- Images only from public/images/

## Style rules

- The first paragraph must stand alone as a description under 160 characters
- Headings start at ## - the filename is the H1
- First person, practitioner tone; write from experience recorded in the notes
- No filler intros ("In today's fast-paced world...") and no filler transitions
- Cite external sources inline with links; keep quotes under 25 words
- Length targets: short 400 words, standard 900, deep 1800 (within 20%)
- Tags from this list (extend deliberately): ai, rag, local-models, obsidian, knowledge-management,
  python, fastapi, azure, engineering-notes
- Prefer concrete numbers, commands, and file paths over abstractions
- One idea per sentence; active voice; plain words over jargon
