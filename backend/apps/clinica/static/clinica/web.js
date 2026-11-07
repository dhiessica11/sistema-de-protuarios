(() => {
  const pacientes = document.querySelector('#pacientes');
  const registros = document.querySelector('#registros');
  const paginas = document.querySelector('#paginas');
  const paginasRegistros = document.querySelector('#paginas-registros');
  const nomePaciente = document.querySelector('#nome-paciente');
  const clinico = document.querySelector('#config-web').dataset.clinico === 'true';
  const fono = document.querySelector('#config-web').dataset.fono === 'true';
  const areaAvaliacao = document.querySelector('#avaliacoes-fono');
  let consultaAvaliacao = 0;
  let selecionado = null;
  let requisicao = 0;

  function elemento(tag, texto, classe) {
    const el = document.createElement(tag);
    el.textContent = texto;
    if (classe) el.className = classe;
    return el;
  }
  async function obter(url) {
    const resposta = await fetch(url, { credentials: 'same-origin', cache: 'no-store' });
    if (!resposta.ok) throw new Error('Não foi possível carregar as informações. Confira sua sessão e tente novamente.');
    return resposta.json();
  }
  function paginar(nav, dados, acao) {
    nav.replaceChildren();
    for (const [rotulo, url] of [['Anterior', dados.previous], ['Próxima', dados.next]]) {
      if (!url) continue;
      const pagina = new URL(url, location.origin).searchParams.get('page');
      if (!/^\d+$/.test(pagina || '')) continue;
      const botao = elemento('button', rotulo, 'secundario');
      botao.type = 'button';
      botao.addEventListener('click', () => acao(pagina));
      nav.append(botao);
    }
  }
  async function carregarPacientes(pagina = 1) {
    pacientes.textContent = 'Carregando pacientes…';
    try {
      const dados = await obter(`/api/v1/pacientes/?page=${encodeURIComponent(pagina)}`);
      pacientes.replaceChildren();
      if (!dados.results.length) pacientes.append(elemento('p', 'Nenhum paciente disponível para seu perfil.', 'ajuda'));
      for (const paciente of dados.results) {
        const botao = elemento('button', '', 'paciente');
        botao.type = 'button';
        botao.append(elemento('strong', paciente.nome_apresentacao), elemento('span', `Prontuário ${paciente.numero_prontuario}`));
        botao.addEventListener('click', () => selecionar(paciente));
        pacientes.append(botao);
      }
      paginar(paginas, dados, carregarPacientes);
    } catch (erro) { pacientes.textContent = erro.message; paginas.replaceChildren(); }
  }
  function selecionar(paciente) {
    selecionado = paciente;
    nomePaciente.textContent = paciente.nome_apresentacao;
    paginasRegistros.replaceChildren();
    if (!clinico) {
      registros.textContent = 'O perfil administrativo não acessa registros clínicos nesta área.';
      return;
    }
    carregarRegistros();
    if (fono) { document.querySelector('#form-avaliacao').reset(); document.querySelector('#mensagem-avaliacao').textContent = ''; areaAvaliacao.hidden = false; carregarAvaliacoes(); }
  }
  async function carregarRegistros(pagina = 1) {
    const atual = ++requisicao;
    const id = selecionado.id;
    registros.textContent = 'Carregando registros…';
    try {
      const dados = await obter(`/api/v1/registros/?paciente=${encodeURIComponent(id)}&page=${encodeURIComponent(pagina)}`);
      if (atual !== requisicao) return;
      registros.replaceChildren();
      if (!dados.results.length) registros.append(elemento('p', 'Nenhum registro disponível para este paciente.', 'ajuda'));
      for (const registro of dados.results) {
        const cartao = elemento('article', '', 'registro');
        const data = new Date(registro.criado_em).toLocaleString('pt-BR');
        cartao.append(elemento('div', `${registro.tipo} · ${registro.categoria} · ${data}`, 'meta'));
        cartao.append(elemento('p', registro.resumo || 'Sem resumo.'));
        if (registro.detalhe) cartao.append(elemento('p', registro.detalhe, 'detalhe'));
        cartao.append(elemento('span', 'Sem assinatura', 'assinatura'));
        registros.append(cartao);
      }
      paginar(paginasRegistros, dados, carregarRegistros);
    } catch (erro) { if (atual === requisicao) { registros.textContent = erro.message; paginasRegistros.replaceChildren(); } }
  }
  async function enviar(url, corpo) {
    const token = document.querySelector('#form-avaliacao [name=csrfmiddlewaretoken]').value;
    const resposta = await fetch(url, {method: 'POST', credentials: 'same-origin', cache: 'no-store', headers: {'Content-Type': 'application/json', 'X-CSRFToken': token}, body: JSON.stringify(corpo)});
    if (!resposta.ok) throw new Error('Não foi possível salvar. Confira os campos, seu vínculo e tente novamente.');
    return resposta.json();
  }
  async function carregarAvaliacoes(pagina = 1) {
    const atual = ++consultaAvaliacao;
    const historico = document.querySelector('#historico-avaliacoes');
    const nav = document.querySelector('#paginas-avaliacoes');
    const origem = document.querySelector('#origem-avaliacao');
    historico.textContent = 'Carregando avaliações…';
    origem.replaceChildren(new Option('Avaliação inicial', ''));
    try {
      const dados = await obter(`/api/v1/avaliacoes-fono/?paciente=${encodeURIComponent(selecionado.id)}&page=${encodeURIComponent(pagina)}`);
      if (atual !== consultaAvaliacao) return;
      historico.replaceChildren();
      if (!dados.results.length) historico.append(elemento('p', 'Nenhuma avaliação cadastrada.', 'ajuda'));
      for (const avaliacao of dados.results) {
        const opcaoOrigem = new Option(`${avaliacao.data} · ${avaliacao.protocolo}`, avaliacao.id);
        opcaoOrigem.dataset.protocolo = avaliacao.protocolo; origem.append(opcaoOrigem);
        const bloco = elemento('article', '', 'registro');
        bloco.append(elemento('h4', `${avaliacao.data} · ${avaliacao.protocolo}`));
        bloco.append(elemento('p', avaliacao.origem ? 'Reavaliação vinculada a uma avaliação anterior.' : 'Avaliação inicial.', 'meta'));
        if (avaliacao.observacoes) bloco.append(elemento('p', avaliacao.observacoes));
        for (const dificuldade of avaliacao.dificuldades) {
          const item = elemento('div', '', 'objetivo');
          item.append(elemento('strong', `Dificuldade: ${dificuldade.descricao}`));
          item.append(elemento('p', `Proposta inicial: ${dificuldade.proposta}`));
          const lista = dificuldade.revisoes;
          for (const revisao of lista) item.append(elemento('p', `${revisao.decisao === 'aprovado' ? 'Aprovado' : 'Não incluído'}: ${revisao.texto}`, 'meta'));
          if (!lista.length) item.append(elemento('p', 'Pendente de revisão', 'assinatura'));
          const texto = document.createElement('textarea'); texto.rows = 2; texto.maxLength = 2000;
          texto.setAttribute('aria-label', 'Texto revisado do objetivo ou justificativa');
          texto.placeholder = 'Escreva o objetivo revisado ou a justificativa';
          const acoes = elemento('div', '', 'paginacao');
          for (const [rotulo, decisao] of [['Aprovar objetivo', 'aprovado'], ['Não incluir', 'descartado']]) {
            const botao = elemento('button', rotulo, 'secundario'); botao.type = 'button';
            botao.addEventListener('click', async () => {
              if (!texto.value.trim()) { texto.focus(); return; }
              botao.disabled = true;
              try { await enviar(`/api/v1/dificuldades-fono/${encodeURIComponent(dificuldade.id)}/revisoes/`, {decisao, texto: texto.value.trim()}); await carregarAvaliacoes(pagina); }
              catch (erro) { alert(erro.message); botao.disabled = false; }
            });
            acoes.append(botao);
          }
          item.append(texto, acoes); bloco.append(item);
        }
        historico.append(bloco);
      }
      paginar(nav, dados, carregarAvaliacoes);
    } catch (erro) { if (atual === consultaAvaliacao) historico.textContent = erro.message; }
  }
  if (fono) document.querySelector('#origem-avaliacao').addEventListener('change', (evento) => {
    const protocolo = evento.target.selectedOptions[0].dataset.protocolo;
    if (protocolo) document.querySelector('#protocolo').value = protocolo;
  });
  if (fono) document.querySelector('#form-avaliacao').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const mensagem = document.querySelector('#mensagem-avaliacao');
    const botao = formulario.querySelector('button[type=submit]');
    const pacienteId = selecionado.id;
    const dificuldades = document.querySelector('#dificuldades').value.split('\n').map(x => x.trim()).filter(Boolean);
    if (dificuldades.length > 50 || dificuldades.some(x => x.length > 500)) { mensagem.textContent = 'Informe até 50 dificuldades de até 500 caracteres cada.'; return; }
    const dados = {paciente: pacienteId, protocolo: document.querySelector('#protocolo').value, data: document.querySelector('#data-avaliacao').value, origem: document.querySelector('#origem-avaliacao').value || null, dificuldades_informadas: dificuldades, observacoes: document.querySelector('#observacoes-avaliacao').value};
    mensagem.textContent = ''; botao.disabled = true;
    try { await enviar('/api/v1/avaliacoes-fono/', dados); if (selecionado.id === pacienteId) { formulario.reset(); mensagem.textContent = 'Avaliação salva. Revise as propostas no histórico.'; await carregarAvaliacoes(); } }
    catch (erro) { mensagem.textContent = erro.message; }
    finally { botao.disabled = false; }
  });
  carregarPacientes();
})();
