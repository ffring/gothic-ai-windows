# Gothic AI для Windows 0.1.0

Первая сборка Gothic AI для Windows 10/11 x64. Её удобнее всего ставить через ИИ-агента: инструкция в [README](https://github.com/ffring/gothic-ai-windows#readme).

## Что внутри

Готовая сборка: игра на движке OpenGothic с ИИ-мостом, ИИ-сервисы, пускатель, `uv` для Python и файлы `Setup-GothicAI.cmd`, `Start-GothicAI.cmd`, `Diagnostics-GothicAI.cmd`. Компилятор и Visual Studio не нужны. Файлов Gothic II в сборке нет: нужна своя русская Gothic II Gold из Steam.

## Состояние

- Сборка собрана на Windows в GitHub Actions и прошла там автоматические тесты: <https://github.com/ffring/GothicAI/actions/runs/40607796695>
- Игру, графику, микрофон и голоса на настоящем игровом компьютере ещё не проверяли.

## Файлы

| Файл | Размер | SHA256 |
|---|---|---|
| `GothicAI-windows-x64-r6-9cadf76.zip` | 52 600 273 байт | `4c1e8b9c0a7a57b13084707848fda29a549c7d4034efece8040a285f56d7f8f7` |
| `GothicAI-windows-x64-r6-9cadf76.manifest.json` | 42 984 байт | `183b7f922c6411e587a1a02658bc0f5e1e1b97e7953773d7f39fe5dc5e20fd92` |
| `SHA256SUMS` | | суммы двух файлов выше |

Те же файлы, что в исходном релизе <https://github.com/ffring/GothicAI/releases/tag/windows-r6.1-9cadf76>.

## Исходный код и лицензии

Исходный код всех программ сборки: <https://github.com/ffring/GothicAI>, коммит `9cadf76b6886cefe48ce61580fe879e8441cb750`. Лицензии — в архиве: `LICENSE` и папка `licenses`.
