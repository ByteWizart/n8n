# Vídeo curto 100% gratuito no n8n

Formulário → LLM gratuito escreve a narração e as cenas → edge-tts gera a voz → `render.py` desenha o vídeo
(bonequinho de graveto + ícones animados, boca sincronizada com a voz, música e efeitos) → MP4 em `./shorts/<id>/video.mp4`.

## Custo: R$ 0
| Etapa | Ferramenta | Observação |
|---|---|---|
| Roteiro e cenas | **Groq** (plano gratuito) | Precisa de conta e chave, sem cartão. Tem limite de uso por minuto/dia |
| Voz | **edge-tts** | Gratuito e sem chave, mas usa o serviço de leitura do Edge de forma não oficial, então pode mudar ou parar |
| Vídeo | `render.py` (Python + Pillow + ffmpeg) | Roda em CPU, sem GPU e sem Chromium |
| Automação | **n8n** self-hosted | Grátis rodando na sua máquina |

## Passo a passo
1. `docker compose up -d --build`
2. Abra `http://localhost:5678` e importe `workflow.json`.
3. Crie uma conta gratuita no Groq, gere uma chave e crie no n8n uma credencial **Header Auth** com Name `Authorization` e Value `Bearer SUA_CHAVE`. Escolha essa credencial no nó **LLM gratuito**.
4. Ative o workflow e abra a URL do formulário.

## Trocar peças por outras gratuitas
- **100% offline, sem conta:** instale o Ollama no seu computador e, no nó do LLM, use a URL `http://host.docker.internal:11434/v1/chat/completions` e o modelo `llama3.1` (sem credencial). Em `Montar pedido`, troque o campo `model`.
- **Voz offline:** troque o comando do nó de voz pelo Piper TTS (voz pt-BR) se o edge-tts parar de funcionar.
- **Voz masculina/feminina:** em `pt-BR-AntonioNeural` use `pt-BR-FranciscaNeural` para voz feminina.

## Ícones disponíveis nas cenas
coração, estrela, sol, lua, terra, gota, raio, relógio, cérebro, olho, lâmpada, foguete, polvo, número (texto grande), pergunta, exclamação. O modelo escolhe um por cena. Para criar novos, adicione uma função `ic_...` em `render/render.py` e registre no dicionário `ICONS`.

## Limites
- Testei o renderizador aqui (todos os ícones e um vídeo completo). **Não testei** o n8n, o Groq nem o edge-tts, porque este ambiente não tem internet.
- O visual é 2D simples, sem o motor 3D do kit anterior. Em troca é rápido: cerca de 2 minutos de render para 20 s de vídeo.
- Se o Groq devolver um JSON fora do formato, o nó **Preparar** avisa e você roda de novo.
- Para renderizar mais rápido em computador fraco, use a variável `SS=1` no comando do nó de render (menos suavização).
