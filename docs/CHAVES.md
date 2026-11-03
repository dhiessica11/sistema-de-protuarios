# Formato dos arquivos de chave

As chaves A, B, C, E e F são arquivos **binários de exatamente 32 bytes**.
Espaços, tabulações e quebras de linha podem ser bytes válidos em qualquer posição.
O carregamento preserva o conteúdo integral, sem `.strip()`, conversão de texto,
decodificação ou remoção de quebras de linha.

Produção usa `/run/secrets/prontuario_key_a` (e os demais nomes correspondentes).
Desenvolvimento usa `secrets_dev/key_a.bin`. Um segredo Docker existente tem
precedência; se tiver tamanho inválido, o carregamento falha, sem recorrer à chave
de desenvolvimento. Um arquivo com 32 bytes mais uma quebra de linha tem 33 bytes
e deve ser rejeitado.

Não adicione newline com `echo`, nem cole uma representação hexadecimal/base64
no lugar dos bytes. Não substitua uma chave que já cifra dados para corrigir um
erro de formato: primeiro recupere os bytes originais pelo procedimento de chaves.
Não exiba o conteúdo dos arquivos em logs ou comandos de diagnóstico.

O script `scripts/generate_dev_keys.py` gera apenas chaves de desenvolvimento e
preserva arquivos já existentes. A geração de produção segue a cerimônia definida
pelo projeto. A chave D de backup continua fora deste carregador.

Regressão automatizada em `backend/apps/core/tests/test_encryption_keys.py`:
preservação dos bytes nas cinco chaves, cifra/decifra, rejeição de tamanhos
inválidos sem fallback e preservação da chave de desenvolvimento.
