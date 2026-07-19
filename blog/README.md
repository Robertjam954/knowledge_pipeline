# Blog

This folder hosts the public blog and its rules.

- `RULES.md` - style + hard rules injected into the drafting prompts
- `posts/` - markdown posts (created by the draft_blog_post tool; also visible in Obsidian)

## Setup (one-time)

The site itself is [nextjs-obsidian-blog-kit](https://github.com/kyoung-jnn/nextjs-obsidian-blog-kit):

```bash
git clone https://github.com/kyoung-jnn/nextjs-obsidian-blog-kit blog-site
cd blog-site && pnpm install && pnpm blog:setup
```

Point its posts directory at this `posts/` folder (or symlink), configure `blog.config.ts`,
and run `pnpm blog:deploy` once to link Vercel. Then create a Deploy Hook
(Vercel project -> Settings -> Git -> Deploy Hooks) and set `KP_VERCEL_DEPLOY_HOOK_URL`.

## Flow

draft (tool, published: false) -> review/edit in Obsidian -> publish_post tool
(flips frontmatter, optional git push, fires deploy hook) -> Vercel builds.

Medium mirror: post_to_medium sends a post as a DRAFT to https://medium.com/@robertjam954
via `KP_MEDIUM_TOKEN` (legacy API; if Medium won't issue a token, the tool returns
paste-ready markdown instead).
