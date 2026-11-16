# RehabAI local AI corpus quality report

Generated: 2026-10-29T19:16:19.495952+00:00

## Counts
- sources collected: 1
- chunks approved for RAG: 1
- conversation samples cleaned: 27
- preference pairs pending: 3
- evaluation items pending: 8
- sources rejected: 0 (no external crawl attempted)
- duplicate rate: 0% after exact user-text deduplication
- average turns per conversation: 2.44
- average assistant response length: 128.18 characters
- human review pending: 38
- license unknown: 0
- unsupported claim count: 0 in approved RAG source

## Distribution
- domains: {'software': 15, 'conversation': 6, 'nutrition': 3, 'safety': 3}
- languages: {'vi': 24, 'en': 3}
- intents: {'AUTH_LOGIN_HELP': 1, 'AUTH_REGISTER_HELP': 1, 'CAMERA_PERMISSION': 1, 'CAMERA_POOR_LIGHT': 1, 'CAMERA_OUT_OF_FRAME': 1, 'SESSION_START_HELP': 1, 'SESSION_STOP_HELP': 1, 'HISTORY_NOT_FOUND': 1, 'PROGRESS_NOT_UPDATED': 1, 'AI_COACH_UNAVAILABLE': 1, 'NETWORK_ERROR': 1, 'FEATURE_EXPLANATION': 1, 'GENERAL_CHAT': 5, 'EMOTIONAL_SUPPORT': 1, 'NUTRITION_GENERAL': 3, 'SAFETY_SUPPORT': 3, 'CAMERA_NOT_FOUND': 1, 'OLLAMA_UNAVAILABLE': 1, 'SESSION_SAVE_ERROR': 1}

## Release gates
- RAG_READY: yes for the existing approved product document only.
- SFT_READY: no; synthetic conversations are CLEANED and require human review.
- EVAL_READY: no; the isolated draft regression set requires human review and must never enter training.

## Limitations
- The small bootstrap corpus does not yet match the optional 30/25/20/10/10/5 target; software support is intentionally overrepresented because it is grounded in verified project behavior.
- No external rehabilitation or nutrition sources were fetched; license and specialist review were intentionally not inferred.
- The nutrition and safety examples are draft evaluation/training candidates, not clinical guidance.
- No fine-tuning was run. Use RAG first and review all synthetic data before any SFT.

## Next steps
1. Have a bilingual reviewer check conversation wording and intent labels.
2. Have an appropriate rehabilitation/nutrition reviewer approve health-related samples.
3. Move only reviewed samples to approved/sft and rerun the manifest.
4. Run the chatbot regression suite before production release.
