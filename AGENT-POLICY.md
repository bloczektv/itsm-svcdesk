<!-- ai-generated: 70% - Claude Code drafted the denylist justifications, reviewed by the author -->
# Agent policy

`.claude/agents/reviewer.md` defines a `reviewer` sub-agent with a `disallowedTools` list. Each entry below
is a blast-radius decision: the tool is not denied because it is dangerous in general, but because letting
the reviewer role use it would let a review turn into an action the author never approved.

- Bash(rm *): the reviewer reads and comments; deleting files is the author's decision, not the reviewer's
- Bash(git push *): only the author decides when review feedback is acted on and pushed to origin, never the reviewer itself
- Bash(docker *): the reviewer assesses code and specs, not container state; it must never start, stop, rebuild or tear down the service
- WebFetch: review must stay confined to this repository's own files, never fetch external pages as evidence
