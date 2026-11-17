# Именованные маршруты p2p на стенде p2p-prototype (снято 17.11.2026)

Источник: `GET https://portal-p2p-prototype.d2.devspark.ru/routes` под авторизованной сессией —
бэкенд отдаёт таблицу `{имя: {path, methods}}`, по которой SPA резолвит `e.request('answers.peer-results', …)`
(без авторизации в таблице только 22 публичных маршрута, с авторизацией — 693). Это самый надёжный способ
узнать реальный путь, вместо угадывания: так найдены `answers.peer-results`, `peer-assignments/redistribute`,
`peer-external-reviewers`, отчёты `peer-review-report.*`.

| Имя маршрута | Методы | Путь |
|---|---|---|
| `answers.peer-results` | GET | `/api/v1/homework/{homework}/answers/{homework_answer}/peer-results` |
| `answers.show` | GET | `/api/v1/homework/{homework}/answers/{homework_answer}` |
| `auth.me` | GET | `/api/v1/auth/me` |
| `homework.answers.examination` | POST | `/api/v1/homework/{homework}/answers/{homework_answer}/examination` |
| `homework.answers.history` | GET | `/api/v1/homework/{homework}/answers/{homework_answer}/history` |
| `homework.answers.index` | GET | `/api/v1/homework/answers` |
| `homework.peer-criteria.index` | GET | `/api/v1/homework/{homework}/peer-criteria` |
| `homework.peer-criteria.store` | POST | `/api/v1/homework/{homework}/peer-criteria` |
| `my.programs.module.homework.peer-reviews.draft` | POST | `/api/v1/my-programs/{program_assignment}/modules/{stream_module}/contents/{stream_content}/homework/answers/{homework_answer}/peer-reviews` |
| `my.programs.module.homework.peer-reviews.finalize` | POST | `/api/v1/my-programs/{program_assignment}/modules/{stream_module}/contents/{stream_content}/homework/answers/{homework_answer}/peer-reviews/finalize` |
| `my.programs.module.homework.peer-submissions.index` | GET | `/api/v1/my-programs/{program_assignment}/modules/{stream_module}/contents/{stream_content}/peer-submissions` |
| `my.programs.module.homework.peer-submissions.show` | GET | `/api/v1/my-programs/{program_assignment}/modules/{stream_module}/contents/{stream_content}/peer-submissions/{homework_answer}` |
| `peer-external.context` | GET | `/api/v1/peer-external/context` |
| `peer-external.exchange` | POST | `/api/v1/peer-external/exchange` |
| `peer-external.session-probe` | GET | `/api/v1/peer-external/session-probe` |
| `peer-external.submissions.index` | GET | `/api/v1/peer-external/submissions` |
| `peer-external.submissions.reviews.draft` | POST | `/api/v1/peer-external/submissions/{homework_answer}/reviews` |
| `peer-external.submissions.reviews.finalize` | POST | `/api/v1/peer-external/submissions/{homework_answer}/reviews/finalize` |
| `peer-external.submissions.show` | GET | `/api/v1/peer-external/submissions/{homework_answer}` |
| `peer-review-report.author.download` | GET | `/api/v1/my/homework-answers/{homework_answer}/peer-review-report` |
| `peer-review-report.staff.download` | GET | `/api/v1/stream-contents/{stream_content}/peer-review-report/download` |
| `peer-review-report.staff.regenerate` | POST | `/api/v1/stream-contents/{stream_content}/peer-review-report/regenerate` |
| `peer-review-report.staff.regenerate-answer` | POST | `/api/v1/homework-answers/{homework_answer}/peer-review-report/regenerate` |
| `programs.streams.modules.contents.peer-assignments.destroy` | DELETE | `/api/v1/programs/{program}/streams/{stream}/modules/{stream_module}/contents/{stream_content}/peer-assignments/{peer_assignment}` |
| `programs.streams.modules.contents.peer-assignments.index` | GET | `/api/v1/programs/{program}/streams/{stream}/modules/{stream_module}/contents/{stream_content}/peer-assignments` |
| `programs.streams.modules.contents.peer-assignments.redistribute` | POST | `/api/v1/programs/{program}/streams/{stream}/modules/{stream_module}/contents/{stream_content}/peer-assignments/redistribute` |
| `programs.streams.modules.contents.peer-assignments.store` | POST | `/api/v1/programs/{program}/streams/{stream}/modules/{stream_module}/contents/{stream_content}/peer-assignments` |
| `programs.streams.modules.contents.peer-assignments.update` | PUT,PATCH | `/api/v1/programs/{program}/streams/{stream}/modules/{stream_module}/contents/{stream_content}/peer-assignments/{peer_assignment}` |
| `programs.streams.modules.contents.peer-external-reviewers.destroy` | DELETE | `/api/v1/programs/{program}/streams/{stream}/modules/{stream_module}/contents/{stream_content}/peer-external-reviewers/{peer_external_reviewer}` |
| `programs.streams.modules.contents.peer-external-reviewers.index` | GET | `/api/v1/programs/{program}/streams/{stream}/modules/{stream_module}/contents/{stream_content}/peer-external-reviewers` |
| `programs.streams.modules.contents.peer-external-reviewers.resend` | POST | `/api/v1/programs/{program}/streams/{stream}/modules/{stream_module}/contents/{stream_content}/peer-external-reviewers/{peer_external_reviewer}/resend` |
| `programs.streams.modules.contents.peer-external-reviewers.revoke` | POST | `/api/v1/programs/{program}/streams/{stream}/modules/{stream_module}/contents/{stream_content}/peer-external-reviewers/{peer_external_reviewer}/revoke` |
| `programs.streams.modules.contents.peer-external-reviewers.store` | POST | `/api/v1/programs/{program}/streams/{stream}/modules/{stream_module}/contents/{stream_content}/peer-external-reviewers` |
| `programs.streams.modules.contents.update-peer-settings` | PUT | `/api/v1/programs/{program}/streams/{stream}/modules/{stream_module}/contents/{stream_content}/peer-settings` |
