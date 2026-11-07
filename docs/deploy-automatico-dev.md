# Atualização automática no mini servidor de desenvolvimento

A automação consulta a branch `desenvolvimento` do GitHub a cada cinco minutos,
enquanto a distribuição WSL e o systemd do usuário estiverem em execução. Ela
não abre portas externas: o mini servidor faz as conexões de saída. É destinada
exclusivamente ao Compose de desenvolvimento e a dados fictícios, não a produção.

## Antes de ativar

No Ubuntu/WSL, confira a branch e o estado do projeto:

```bash
cd /home/dpl/projetos/sistema-de-protuarios
git status
git branch --show-current
ps -p 1 -o comm=
systemctl --user status
```

A branch deve ser `desenvolvimento`, sem alterações locais não ignoradas. O último
comando precisa conseguir falar com o gerenciador systemd do usuário. Se o PID 1
não for `systemd` ou o comando falhar, o WSL ainda precisa ser configurado para
systemd antes de seguir. Não habilite a automação em um ambiente com dados reais.
O Docker Desktop deve estar ativo, com integração à distribuição Ubuntu, e o usuário
precisa conseguir executar `docker compose` sem prompts. O arquivo `.env` precisa
conter exatamente `DJANGO_SETTINGS_MODULE=config.settings.dev`.

## Ativar

A partir da pasta do projeto, depois que esta mudança estiver integrada ao GitHub:

```bash
git pull --ff-only origin desenvolvimento
mkdir -p ~/.config/systemd/user
cp infra/systemd/prontuario-atualiza.service ~/.config/systemd/user/
cp infra/systemd/prontuario-atualiza.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now prontuario-atualiza.timer
systemctl --user start prontuario-atualiza.service
```

A última linha inicia uma primeira verificação agora; a primeira execução pode
reconstruir os containers e reaplicar o comando de migrations mesmo se o commit já
estiver instalado. O timer verificará mudanças a cada cinco minutos depois disso.
Quando o WSL estiver parado, o Windows estiver suspenso ou o Docker Desktop não
estiver pronto, a atualização não acontece; o timer não inicia o Windows nem o
WSL. Não há acesso deste ambiente da nuvem ao mini servidor para ativá-lo ou
confirmar suas configurações.

## Verificar e pausar

```bash
systemctl --user status prontuario-atualiza.timer
systemctl --user list-timers prontuario-atualiza.timer
journalctl --user -u prontuario-atualiza.service -n 60 --no-pager
curl -fsS http://127.0.0.1:8000/health/
```

Para interromper as verificações automáticas:

```bash
systemctl --user disable --now prontuario-atualiza.timer
```

## Regras e limitações

- O script verifica o remoto esperado, a branch local, alterações de Git e a
  configuração dev. Busca o commit remoto e consulta o CI do GitHub: exige uma
  execução `push` bem-sucedida do workflow CI para aquele commit e branch. Se o CI
  falhar, estiver pendente ou não puder ser consultado, não atualiza. A API pública
  do GitHub pode limitar consultas; neste caso, a próxima execução tenta novamente.
- Antes de trocar arquivos, para web e worker porque o Compose monta o código do
  diretório local. Em seguida faz fast-forward, constrói as imagens, aguarda banco
  e Redis, aplica migrations, inicia web e worker e consulta `/health/`. O health
  check confirma a resposta do endpoint, não valida todos os fluxos da aplicação.
- Se a atualização falhar depois de parar a aplicação, ela pode permanecer parada
  ou parcialmente atualizada. Consulte o journal e os logs do Compose. Uma execução
  seguinte tentará de novo. Não há rollback automático do código ou das migrations.
- Volumes do banco não são apagados. A automação não cria nem valida backups, não
  configura produção e não substitui MFA, auditoria ou assinatura. Seu uso é para
  dados fictícios; executar migrations automaticamente com dados reais exige um
  processo de backup, restauração e aprovação de versão definido à parte.
- Como o timer usa uma cópia das units em `~/.config/systemd/user`, atualizações
  dessas units no repositório exigem copiá-las de novo e executar `daemon-reload`.
  O script em `scripts/` é lido diretamente do repositório a cada execução.
