(() => {
  const pacientes = document.querySelector('#pacientes');
  const registros = document.querySelector('#registros');
  const paginas = document.querySelector('#paginas');
  const paginasRegistros = document.querySelector('#paginas-registros');
  const nomePaciente = document.querySelector('#nome-paciente');
  const clinico = document.querySelector('#config-web').dataset.clinico === 'true';
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
  carregarPacientes();
})();
