Output demo/demo.gif

Set Shell "bash"
Set FontSize 15
Set Width 1000
Set Height 640
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 35ms

Type "# aipreflight: one command, one ship/block verdict. No GPU, no live endpoint."
Enter
Sleep 1s

Type "# 1. A hosted-API app: cost, evals, observability, rollback."
Enter
Sleep 600ms
Type "aipreflight check --profile profiles/app.yml"
Enter
Sleep 3s

Type "cat runs/latest/aipreflight-report.md"
Enter
Sleep 4s

Type "# 2. Now a RAG system whose retrieval just regressed. The service is still up."
Enter
Sleep 800ms
Type "AIPREFLIGHT_RAG_BROKEN=1 aipreflight check --profile profiles/rag.yml"
Enter
Sleep 3s

Type "cat runs/latest/aipreflight-report.md"
Enter
Sleep 4s

Type "# Verdict: FAIL. Bad retrieval blocks the deploy even though nothing went down."
Enter
Sleep 2s
