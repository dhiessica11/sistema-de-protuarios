(() => {
  const pacientes = document.querySelector('#pacientes');
  const registros = document.querySelector('#registros');
  const paginas = document.querySelector('#paginas');
  const paginasRegistros = document.querySelector('#paginas-registros');
  const nomePaciente = document.querySelector('#nome-paciente');
  const clinico = document.querySelector('#config-web').dataset.clinico === 'true';
  const fono = document.querySelector('#config-web').dataset.fono === 'true';
  const areaAvaliacao = document.querySelector('#avaliacoes-fono');
  const adminTeste = document.querySelector('#config-web').dataset.adminTeste === 'true';
  let consultaCadastro = 0;
  let consultaResponsaveis = 0;
  let consultaAvaliacao = 0;
  let consultaPlano = 0;
  let consultaSessao = 0;
  let consultaEvolucao = 0;
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
    if (fono) for (const tipo of ['avaliacao', 'plano', 'sessao']) { document.querySelector(`#edicao-${tipo}`).textContent = ''; document.querySelector(`#cancelar-${tipo}`).hidden = true; }
    nomePaciente.textContent = paciente.nome_apresentacao;
    if (adminTeste) { document.querySelector('#cadastro-admin').hidden = false; document.querySelector('#form-novo-responsavel').reset(); document.querySelector('#mensagem-responsavel-novo').textContent = ''; carregarCadastro(); carregarResponsaveis(); }
    paginasRegistros.replaceChildren();
    if (!clinico) {
      registros.textContent = 'O perfil administrativo não acessa registros clínicos nesta área.';
      return;
    }
    carregarRegistros();
    if (fono) { document.querySelector('#form-avaliacao').reset(); document.querySelector('#mensagem-avaliacao').textContent = ''; areaAvaliacao.hidden = false; document.querySelector('#planos-fono').hidden = false; document.querySelector('#form-plano').reset(); document.querySelector('#mensagem-plano').textContent = ''; document.querySelector('#sessoes-fono').hidden = false; document.querySelector('#evolucao-fono').hidden = false; document.querySelector('#form-evolucao').reset(); document.querySelector('#resultado-evolucao').textContent = 'Selecione um objetivo e um período.'; consultaEvolucao++;  document.querySelector('#form-sessao').reset(); document.querySelector('#tentativas-sessao').replaceChildren(); document.querySelector('#mensagem-sessao').textContent = ''; carregarAvaliacoes(); carregarPlanos(); carregarSessoes(); }
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
        if (adminTeste) cartao.append(elemento('p', `Autoria: ${registro.autor}`, 'meta'));
        cartao.append(elemento('p', registro.resumo || 'Sem resumo.'));
        if (registro.detalhe) cartao.append(elemento('p', registro.detalhe, 'detalhe'));
        if (adminTeste && registro.origem) cartao.append(elemento('p', `Registro de origem: ${registro.origem}`, 'meta'));
        if (adminTeste && registro.justificativa) cartao.append(elemento('p', `Justificativa: ${registro.justificativa}`));
        if (adminTeste && registro.contato_validacao) cartao.append(elemento('p', `Contato de validação: ${registro.contato_validacao}`));
        cartao.append(elemento('span', 'Sem assinatura', 'assinatura'));
        registros.append(cartao);
      }
      paginar(paginasRegistros, dados, carregarRegistros);
    } catch (erro) { if (atual === requisicao) { registros.textContent = erro.message; paginasRegistros.replaceChildren(); } }
  }
  async function carregarCadastro() {
    const atual = ++consultaCadastro;
    const area = document.querySelector('#dados-cadastrais');
    area.textContent = 'Carregando cadastro…';
    try {
      const dados = await obter(`/api/v1/pacientes/${encodeURIComponent(selecionado.id)}/`);
      if (atual !== consultaCadastro) return;
      area.replaceChildren();
      const campos = [['Nome civil', 'nome_civil'], ['Nome social', 'nome_social'], ['CPF', 'cpf'], ['Nascimento', 'data_nascimento'], ['Sexo', 'sexo'], ['Nacionalidade', 'nacionalidade'], ['Naturalidade', 'naturalidade'], ['Endereço', 'endereco_cifrado'], ['Telefone', 'telefone_cifrado'], ['Status', 'status'], ['Encerramento', 'data_encerramento']];
      for (const [rotulo, chave] of campos) if (dados[chave]) area.append(elemento('p', `${rotulo}: ${dados[chave]}`));
    } catch (erro) { if (atual === consultaCadastro) area.textContent = erro.message; }
  }
  async function carregarResponsaveis(pagina = 1) {
    const atual = ++consultaResponsaveis;
    const area = document.querySelector('#responsaveis-admin');
    const nav = document.querySelector('#paginas-responsaveis');
    area.textContent = 'Carregando responsáveis…';
    try {
      const dados = await obter(`/api/v1/responsaveis/?paciente=${encodeURIComponent(selecionado.id)}&page=${encodeURIComponent(pagina)}`);
      if (atual !== consultaResponsaveis) return;
      area.replaceChildren();
      if (!dados.results.length) area.append(elemento('p', 'Nenhum responsável cadastrado.', 'ajuda'));
      for (const pessoa of dados.results) {
        const bloco = elemento('article', '', 'registro');
        const campos = [['Nome', 'nome'], ['CPF', 'cpf'], ['Vínculo', 'vinculo'], ['Telefone', 'telefone_cifrado'], ['E-mail', 'email'], ['Comprovante', 'comprovante_vinculo_pendente']];
        for (const [rotulo, chave] of campos) if (pessoa[chave]) bloco.append(elemento('p', `${rotulo}: ${pessoa[chave]}`));
        bloco.append(elemento('p', `Ativo: ${pessoa.ativo ? 'sim' : 'não'} · Responsável principal: ${pessoa.eh_responsavel_legal_principal ? 'sim' : 'não'} · Guarda compartilhada: ${pessoa.guarda_compartilhada ? 'sim' : 'não'}`));
        area.append(bloco);
      }
      paginar(nav, dados, carregarResponsaveis);
    } catch (erro) { if (atual === consultaResponsaveis) { area.textContent = erro.message; nav.replaceChildren(); } }
  }
  async function carregarClinicas() {
    const seletor = document.querySelector('#clinica-paciente');
    const ajuda = document.querySelector('#ajuda-clinica');
    try {
      const dados = await obter('/api/v1/clinicas/');
      seletor.replaceChildren(new Option('Selecione uma clínica', ''));
      for (const clinica of dados.results) seletor.append(new Option(clinica.nome, clinica.id));
      if (!dados.results.length) {
        ajuda.replaceChildren(document.createTextNode('Nenhuma clínica cadastrada. '));
        const link = elemento('a', 'Cadastre uma clínica fictícia na administração.');
        link.href = '/admin/clinica/clinica/add/'; ajuda.append(link);
      } else if (dados.count > dados.results.length) {
        ajuda.textContent = 'A lista exibe as primeiras 25 clínicas cadastradas.';
      } else ajuda.textContent = '';
    } catch (erro) { seletor.replaceChildren(new Option('Não foi possível carregar', '')); ajuda.textContent = erro.message; }
  }
  async function enviarCadastro(url, corpo, formulario) {
    const token = formulario.querySelector('[name=csrfmiddlewaretoken]').value;
    let resposta;
    try { resposta = await fetch(url, {method:'POST', credentials:'same-origin', cache:'no-store', headers:{'Content-Type':'application/json', 'X-CSRFToken':token}, body:JSON.stringify(corpo)}); }
    catch (_) { throw new Error('Conexão interrompida. Confira a lista antes de tentar novamente, pois o cadastro pode ter sido salvo.'); }
    if (resposta.ok) return resposta.json();
    let erro = null;
    try { erro = await resposta.json(); } catch (_) { /* Resposta sem JSON. */ }
    if (resposta.status === 400 && erro && typeof erro === 'object' && !Array.isArray(erro)) {
      const mensagens = Object.entries(erro).map(([campo, texto]) => `${campo}: ${Array.isArray(texto) ? texto.join(' ') : String(texto)}`);
      throw new Error(mensagens.join(' · ') || 'Confira os campos informados.');
    }
    throw new Error('Não foi possível confirmar o cadastro. Confira a lista antes de tentar novamente.');
  }
  if (adminTeste) {
    carregarClinicas();
    document.querySelector('#form-novo-paciente').addEventListener('submit', async (evento) => {
      evento.preventDefault();
      const form = evento.currentTarget, botao = form.querySelector('button[type=submit]');
      const mensagem = document.querySelector('#mensagem-paciente-novo');
      const selecaoAnterior = selecionado?.id || null;
      const dados = {clinica:document.querySelector('#clinica-paciente').value, nome_civil:document.querySelector('#nome-paciente-novo').value.trim(), nome_social:document.querySelector('#social-paciente-novo').value.trim(), data_nascimento:document.querySelector('#nascimento-paciente-novo').value, sexo:document.querySelector('#sexo-paciente-novo').value, cpf:document.querySelector('#cpf-paciente-novo').value.trim()};
      botao.disabled = true; mensagem.textContent = '';
      try {
        const paciente = await enviarCadastro('/api/v1/pacientes/', dados, form);
        form.reset(); mensagem.textContent = 'Paciente fictício cadastrado.';
        if ((selecionado?.id || null) === selecaoAnterior) selecionar(paciente);
        await carregarPacientes();
      } catch (erro) { mensagem.textContent = erro.message; }
      finally { botao.disabled = false; }
    });
    document.querySelector('#form-novo-responsavel').addEventListener('submit', async (evento) => {
      evento.preventDefault();
      if (!selecionado) return;
      const form = evento.currentTarget, botao = form.querySelector('button[type=submit]');
      const mensagem = document.querySelector('#mensagem-responsavel-novo');
      const pacienteId = selecionado.id;
      const dados = {paciente:pacienteId, nome:document.querySelector('#nome-responsavel-novo').value.trim(), cpf:document.querySelector('#cpf-responsavel-novo').value.trim(), vinculo:document.querySelector('#vinculo-responsavel-novo').value, telefone_cifrado:document.querySelector('#telefone-responsavel-novo').value.trim(), email:document.querySelector('#email-responsavel-novo').value.trim(), eh_responsavel_legal_principal:document.querySelector('#principal-responsavel-novo').checked};
      botao.disabled = true; mensagem.textContent = '';
      try {
        await enviarCadastro('/api/v1/responsaveis/', dados, form);
        if (selecionado?.id === pacienteId) { form.reset(); mensagem.textContent = 'Responsável fictício cadastrado.'; await carregarResponsaveis(); }
      } catch (erro) { if (selecionado?.id === pacienteId) mensagem.textContent = erro.message; }
      finally { botao.disabled = false; }
    });
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
    const opcoesPlano = document.querySelector('#objetivos-plano');
    opcoesPlano.replaceChildren();
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
        bloco.append(elemento('p', `Autoria: ${avaliacao.autor}`, 'meta'));
        if (avaliacao.corrige) bloco.append(elemento('p', 'Correção de uma versão anterior.', 'meta'));
        if (avaliacao.corrigida) bloco.append(elemento('p', 'Versão corrigida; mantida no histórico.', 'meta'));
        if (!avaliacao.corrigida) {
          const corrigir = elemento('button', 'Corrigir avaliação', 'secundario'); corrigir.type = 'button';
          corrigir.addEventListener('click', () => {
            document.querySelector('#corrige-avaliacao').value = avaliacao.id;
            document.querySelector('#data-avaliacao').value = avaliacao.data;
            document.querySelector('#protocolo').value = avaliacao.protocolo;
            document.querySelector('#observacoes-avaliacao').value = avaliacao.observacoes;
            document.querySelector('#dificuldades').value = avaliacao.dificuldades.map(x => x.descricao).join('\n');
            if (avaliacao.origem && !Array.from(origem.options).some(o => o.value === avaliacao.origem)) origem.append(new Option('Avaliação anterior vinculada', avaliacao.origem));
            origem.value = avaliacao.origem || '';
            document.querySelector('#edicao-avaliacao').textContent = 'Corrigindo uma avaliação: ao salvar, será criada uma nova versão e as dificuldades precisarão de nova revisão.';
            document.querySelector('#cancelar-avaliacao').hidden = false;
            document.querySelector('#form-avaliacao').scrollIntoView({behavior:'smooth'});
          });
          bloco.append(corrigir);
        }
        bloco.append(elemento('p', avaliacao.origem ? 'Reavaliação vinculada a uma avaliação anterior.' : 'Avaliação inicial.', 'meta'));
        if (avaliacao.observacoes) bloco.append(elemento('p', avaliacao.observacoes));
        for (const dificuldade of avaliacao.dificuldades) {
          const item = elemento('div', '', 'objetivo');
          item.append(elemento('strong', `Dificuldade: ${dificuldade.descricao}`));
          item.append(elemento('p', `Proposta inicial: ${dificuldade.proposta}`));
          const lista = dificuldade.revisoes;
          const ultima = lista[lista.length - 1];
          if (!avaliacao.corrigida && ultima && ultima.decisao === 'aprovado') {
            const linha = elemento('div', '', 'opcao-plano');
            const label = elemento('label', '', 'opcao-label');
            const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.value = ultima.id;
            label.append(checkbox, document.createTextNode(` ${ultima.texto}`));
            const meta = document.createElement('textarea'); meta.rows = 2; meta.maxLength = 2000; meta.placeholder = 'Meta para este objetivo'; meta.setAttribute('aria-label', `Meta: ${ultima.texto}`);
            linha.append(label, meta); opcoesPlano.append(linha);
          }
          for (const revisao of lista) item.append(elemento('p', `${revisao.decisao === 'aprovado' ? 'Aprovado' : 'Não incluído'}: ${revisao.texto}`, 'meta'));
          if (!lista.length) item.append(elemento('p', 'Pendente de revisão', 'assinatura'));
          if (avaliacao.corrigida) { bloco.append(item); continue; }
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
      if (!opcoesPlano.children.length) opcoesPlano.append(elemento('p', 'Nenhum objetivo aprovado nesta página.', 'ajuda'));
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
    const dados = {paciente: pacienteId, protocolo: document.querySelector('#protocolo').value, data: document.querySelector('#data-avaliacao').value, origem: document.querySelector('#origem-avaliacao').value || null, corrige: document.querySelector('#corrige-avaliacao').value || null, dificuldades_informadas: dificuldades, observacoes: document.querySelector('#observacoes-avaliacao').value};
    mensagem.textContent = ''; botao.disabled = true;
    try { await enviar('/api/v1/avaliacoes-fono/', dados); if (selecionado.id === pacienteId) { formulario.reset(); document.querySelector('#edicao-avaliacao').textContent = ''; document.querySelector('#cancelar-avaliacao').hidden = true; mensagem.textContent = 'Avaliação salva. Revise as propostas no histórico.'; await carregarAvaliacoes(); } }
    catch (erro) { mensagem.textContent = erro.message; }
    finally { botao.disabled = false; }
  });
  async function carregarPlanos(pagina = 1) {
    const atual = ++consultaPlano;
    const historico = document.querySelector('#historico-planos');
    const nav = document.querySelector('#paginas-planos');
    historico.textContent = 'Carregando planos…';
    const objetivoSessao = document.querySelector('#objetivo-sessao');
    objetivoSessao.replaceChildren(new Option('Sem objetivo vinculado', ''));
    const objetivoEvolucao = document.querySelector('#objetivo-evolucao');
    objetivoEvolucao.replaceChildren(new Option('Selecione um objetivo', ''));
    consultaEvolucao++;
    document.querySelector('#resultado-evolucao').textContent = 'Selecione um objetivo e um período.';
    try {
      const dados = await obter(`/api/v1/planos-fono/?paciente=${encodeURIComponent(selecionado.id)}&page=${encodeURIComponent(pagina)}`);
      if (atual !== consultaPlano) return;
      historico.replaceChildren();
      if (!dados.results.length) historico.append(elemento('p', 'Nenhum plano cadastrado.', 'ajuda'));
      for (const plano of dados.results) {
        const bloco = elemento('article', '', 'registro');
        bloco.append(elemento('h4', `Plano de ${plano.inicio} até ${plano.fim}`));
        bloco.append(elemento('p', `Autoria: ${plano.autor}`, 'meta'));
        if (plano.corrige) bloco.append(elemento('p', 'Correção de uma versão anterior.', 'meta'));
        if (plano.corrigido) bloco.append(elemento('p', 'Versão corrigida; mantida no histórico.', 'meta'));
        if (!plano.corrigido) {
          const corrigir = elemento('button', 'Corrigir plano', 'secundario'); corrigir.type = 'button';
          corrigir.addEventListener('click', () => {
            const form = document.querySelector('#form-plano'); form.reset();
            document.querySelector('#corrige-plano').value = plano.id;
            document.querySelector('#inicio-plano').value = plano.inicio;
            document.querySelector('#fim-plano').value = plano.fim;
            document.querySelector('#recursos-plano').value = plano.recursos;
            document.querySelector('#orientacoes-plano').value = plano.orientacoes;
            let pendentes = 0;
            for (const item of plano.itens) {
              const linha = Array.from(document.querySelectorAll('.opcao-plano')).find(el => el.querySelector('input').value === item.revisao);
              if (linha) { linha.querySelector('input').checked = true; linha.querySelector('textarea').value = item.meta; } else pendentes++;
            }
            document.querySelector('#edicao-plano').textContent = pendentes ? 'Alguns objetivos não estão aprovados na página atual. Selecione novamente os objetivos para corrigir o plano.' : 'Corrigindo plano: ao salvar, será criada uma nova versão.';
            document.querySelector('#cancelar-plano').hidden = false;
            form.scrollIntoView({behavior:'smooth'});
          });
          bloco.append(corrigir);
        }
        bloco.append(elemento('span', 'Sem assinatura', 'assinatura'));
        for (const item of plano.itens) {
          objetivoSessao.append(new Option(`${plano.inicio} · ${item.objetivo}`, item.id));
          objetivoEvolucao.append(new Option(`${plano.inicio} · ${item.objetivo}`, item.id));
          bloco.append(elemento('p', `Dificuldade: ${item.dificuldade}`));
          bloco.append(elemento('p', `Objetivo: ${item.objetivo}`));
          bloco.append(elemento('p', `Meta: ${item.meta}`));
        }
        if (plano.recursos) bloco.append(elemento('p', `Recursos: ${plano.recursos}`));
        if (plano.orientacoes) bloco.append(elemento('p', `Orientações: ${plano.orientacoes}`));
        historico.append(bloco);
      }
      paginar(nav, dados, carregarPlanos);
    } catch (erro) { if (atual === consultaPlano) historico.textContent = erro.message; }
  }
  if (fono) document.querySelector('#form-plano').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const form = evento.currentTarget;
    const mensagem = document.querySelector('#mensagem-plano');
    const botao = form.querySelector('button[type=submit]');
    const pacienteId = selecionado.id;
    const itens = Array.from(document.querySelectorAll('.opcao-plano')).filter(el => el.querySelector('input').checked).map(el => ({revisao: el.querySelector('input').value, meta: el.querySelector('textarea').value.trim()}));
    if (!itens.length || itens.some(item => !item.meta)) { mensagem.textContent = 'Selecione ao menos um objetivo e informe uma meta para cada um.'; return; }
    const dados = {paciente: pacienteId, corrige: document.querySelector('#corrige-plano').value || null, inicio: document.querySelector('#inicio-plano').value, fim: document.querySelector('#fim-plano').value, recursos: document.querySelector('#recursos-plano').value, orientacoes: document.querySelector('#orientacoes-plano').value, itens_informados: itens};
    mensagem.textContent = ''; botao.disabled = true;
    try { await enviar('/api/v1/planos-fono/', dados); if (selecionado.id === pacienteId) { form.reset(); document.querySelector('#edicao-plano').textContent = ''; document.querySelector('#cancelar-plano').hidden = true; mensagem.textContent = 'Plano de teste salvo sem assinatura.'; await carregarPlanos(); } }
    catch (erro) { mensagem.textContent = erro.message; }
    finally { botao.disabled = false; }
  });
  const codigosTentativa = [['I', 'Independente'], ['E', 'Erro'], ['G', 'Gestual'], ['VP', 'Verbal parcial'], ['VT', 'Verbal total'], ['FP', 'Físico parcial'], ['FT', 'Físico total'], ['VS', 'Visual / posicional']];
  function adicionarTentativa(valor = '') {
    const lista = document.querySelector('#tentativas-sessao');
    if (lista.children.length >= 100) { document.querySelector('#mensagem-sessao').textContent = 'Limite de 100 tentativas por sessão.'; return; }
    const linha = elemento('div', '', 'linha-tentativa');
    const select = document.createElement('select'); select.required = true; select.setAttribute('aria-label', 'Resultado da tentativa');
    select.append(new Option('Selecione o resultado', ''));
    for (const [codigo, descricao] of codigosTentativa) select.append(new Option(`${codigo} — ${descricao}`, codigo));
    const remover = elemento('button', 'Remover', 'secundario'); remover.type = 'button'; remover.addEventListener('click', () => linha.remove());
    select.value = valor; linha.append(select, remover); lista.append(linha);
  }
  if (fono) document.querySelector('#adicionar-tentativa').addEventListener('click', () => adicionarTentativa());
  async function carregarSessoes(pagina = 1) {
    const atual = ++consultaSessao;
    const historico = document.querySelector('#historico-sessoes');
    const nav = document.querySelector('#paginas-sessoes');
    historico.textContent = 'Carregando sessões…';
    try {
      const dados = await obter(`/api/v1/sessoes-fono/?paciente=${encodeURIComponent(selecionado.id)}&page=${encodeURIComponent(pagina)}`);
      if (atual !== consultaSessao) return;
      historico.replaceChildren();
      if (!dados.results.length) historico.append(elemento('p', 'Nenhuma sessão cadastrada.', 'ajuda'));
      for (const sessao of dados.results) {
        const bloco = elemento('article', '', 'registro');
        bloco.append(elemento('h4', `${sessao.data} · ${sessao.atividade}`));
        bloco.append(elemento('p', `Autoria: ${sessao.autor}`, 'meta'));
        if (sessao.corrige) bloco.append(elemento('p', 'Correção de uma versão anterior.', 'meta'));
        if (sessao.corrigida) bloco.append(elemento('p', 'Versão corrigida; mantida no histórico e excluída da evolução.', 'meta'));
        if (!sessao.corrigida) {
          const corrigir = elemento('button', 'Corrigir sessão', 'secundario'); corrigir.type = 'button';
          corrigir.addEventListener('click', () => {
            const form = document.querySelector('#form-sessao'); form.reset();
            document.querySelector('#corrige-sessao').value = sessao.id;
            document.querySelector('#data-sessao').value = sessao.data;
            document.querySelector('#atividade-sessao').value = sessao.atividade;
            document.querySelector('#observacoes-sessao').value = sessao.observacoes;
            const objetivo = document.querySelector('#objetivo-sessao');
            if (sessao.objetivo && !Array.from(objetivo.options).some(o => o.value === sessao.objetivo)) objetivo.append(new Option(sessao.objetivo_texto || 'Objetivo vinculado', sessao.objetivo));
            objetivo.value = sessao.objetivo || '';
            document.querySelector('#tentativas-sessao').replaceChildren();
            for (const codigo of sessao.resultados.tentativas) adicionarTentativa(codigo);
            document.querySelector('#edicao-sessao').textContent = 'Corrigindo sessão: ao salvar, uma nova versão substituirá a anterior nos gráficos.';
            document.querySelector('#cancelar-sessao').hidden = false;
            form.scrollIntoView({behavior:'smooth'});
          });
          bloco.append(corrigir);
        }
        if (sessao.objetivo_texto) bloco.append(elemento('p', `Objetivo: ${sessao.objetivo_texto}`));
        const r = sessao.resultados;
        bloco.append(elemento('p', `Tentativas: ${r.total}${r.total ? ` · ${r.tentativas.join(', ')}` : ' · Sem dados'}`));
        if (r.total) bloco.append(elemento('p', `Independentes: ${r.percentual_independente}% · Com ajuda: ${r.percentual_ajuda}% · Erros: ${r.percentual_erro}%`, 'meta'));
        if (sessao.observacoes) bloco.append(elemento('p', sessao.observacoes));
        bloco.append(elemento('span', 'Sem assinatura', 'assinatura'));
        historico.append(bloco);
      }
      paginar(nav, dados, carregarSessoes);
    } catch (erro) { if (atual === consultaSessao) { historico.textContent = erro.message; nav.replaceChildren(); } }
  }
  if (fono) document.querySelector('#form-sessao').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const form = evento.currentTarget;
    const mensagem = document.querySelector('#mensagem-sessao');
    const botao = form.querySelector('button[type=submit]');
    const pacienteId = selecionado.id;
    const tentativas = Array.from(document.querySelectorAll('#tentativas-sessao select')).map(select => select.value);
    const dados = {paciente: pacienteId, corrige: document.querySelector('#corrige-sessao').value || null, data: document.querySelector('#data-sessao').value, atividade: document.querySelector('#atividade-sessao').value, objetivo: document.querySelector('#objetivo-sessao').value || null, observacoes: document.querySelector('#observacoes-sessao').value, tentativas};
    mensagem.textContent = ''; botao.disabled = true;
    try { await enviar('/api/v1/sessoes-fono/', dados); if (selecionado.id === pacienteId) { form.reset(); document.querySelector('#edicao-sessao').textContent = ''; document.querySelector('#cancelar-sessao').hidden = true; document.querySelector('#tentativas-sessao').replaceChildren(); consultaEvolucao++; document.querySelector('#resultado-evolucao').textContent = 'A sessão foi salva. Atualize a evolução para ver os resultados.'; mensagem.textContent = 'Sessão de teste salva sem assinatura.'; await carregarSessoes(); } }
    catch (erro) { mensagem.textContent = erro.message; }
    finally { botao.disabled = false; }
  });
  if (fono) for (const id of ['#objetivo-evolucao', '#inicio-evolucao', '#fim-evolucao']) document.querySelector(id).addEventListener('change', () => {
    consultaEvolucao++;
    document.querySelector('#resultado-evolucao').textContent = 'Selecione Ver evolução para atualizar os resultados.';
  });
  if (fono) document.querySelector('#form-evolucao').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const resultado = document.querySelector('#resultado-evolucao');
    const paciente = selecionado.id;
    const objetivo = document.querySelector('#objetivo-evolucao').value;
    const inicio = document.querySelector('#inicio-evolucao').value;
    const fim = document.querySelector('#fim-evolucao').value;
    const atual = ++consultaEvolucao;
    const params = new URLSearchParams({paciente, objetivo, inicio, fim});
    resultado.textContent = 'Carregando evolução…';
    try {
      const dados = await obter(`/api/v1/sessoes-fono/evolucao/?${params}`);
      if (atual !== consultaEvolucao) return;
      resultado.replaceChildren();
      if (!dados.pontos.length) { resultado.append(elemento('p', 'Nenhuma sessão registrada para este objetivo no período.', 'ajuda')); return; }
      for (const ponto of dados.pontos) {
        const bloco = elemento('article', '', 'registro');
        const data = ponto.data.split('-').reverse().join('/');
        bloco.append(elemento('strong', `${data} · ${ponto.sessoes} sessão(ões) · ${ponto.total} tentativa(s)`));
        if (!ponto.total) {
          bloco.append(elemento('p', 'Sem tentativas registradas: sem dados para percentuais.', 'ajuda'));
        } else {
          for (const [titulo, total, percentual, classe] of [['Independentes', ponto.independentes, ponto.percentual_independentes, 'independente'], ['Com ajuda', ponto.ajudas, ponto.percentual_ajudas, 'ajuda-grafico'], ['Erros', ponto.erros, ponto.percentual_erros, 'erro-grafico']]) {
            bloco.append(elemento('p', `${titulo}: ${total} de ${ponto.total} (${percentual}%)`, 'meta'));
            const trilho = elemento('div', '', 'barra-trilho');
            trilho.setAttribute('aria-hidden', 'true');
            const barra = elemento('div', '', `barra ${classe}`); barra.style.width = `${percentual}%`;
            trilho.append(barra); bloco.append(trilho);
          }
        }
        resultado.append(bloco);
      }
    } catch (erro) { if (atual === consultaEvolucao) resultado.textContent = 'Não foi possível carregar a evolução. Confira o período de até 366 dias e tente novamente.'; }
  });
  if (fono) for (const tipo of ['avaliacao', 'plano', 'sessao']) document.querySelector(`#cancelar-${tipo}`).addEventListener('click', () => {
    document.querySelector(`#form-${tipo}`).reset();
    document.querySelector(`#edicao-${tipo}`).textContent = '';
    document.querySelector(`#cancelar-${tipo}`).hidden = true;
    if (tipo === 'sessao') document.querySelector('#tentativas-sessao').replaceChildren();
  });
  carregarPacientes();
})();
