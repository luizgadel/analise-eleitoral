export const URL_APURACAO =
  "https://resultados.tse.jus.br/oficial/ele2026/6259/dados/am/am-c0006-e006259-u.json";

export const INTERVALO_APURACAO_MS = 50_000;

const pedidos = new Map();

export function baixarApuracao(url = URL_APURACAO) {
  if (!pedidos.has(url)) {
    const pedido = fetch(url, { cache: "no-cache" })
      .then(async (resposta) => {
        if (!resposta.ok) throw new Error("Não foi possível ler a apuração do TSE.");
        return resposta.text();
      })
      .finally(() => {
        pedidos.delete(url);
      });
    pedidos.set(url, pedido);
  }
  return pedidos.get(url);
}

function semAcento(texto) {
  return texto.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

function inteiro(valor) {
  const digitos = String(valor ?? "").replace(/\D/g, "");
  return digitos ? Number(digitos) : 0;
}

export function votoValido(candidato) {
  const destinacao = semAcento(String(candidato?.dvt || ""));
  if (!destinacao.includes("valido") || destinacao.includes("anulado") || destinacao.includes("legenda")) {
    return 0;
  }
  return inteiro(candidato?.vap);
}

function cargoDeputado(bruto, codigo) {
  const cargos = bruto?.carg || [];
  return cargos.find((item) => String(item.cd) === String(codigo)) || cargos[0];
}

function grupos(cargo) {
  const federacoes = new Map((cargo.fed || []).map((item) => [String(item.n), item]));
  const blocos = new Map();
  for (const agrupamento of cargo.agr || []) {
    for (const partido of agrupamento.par || []) {
      const nfed = String(partido.nfed || "");
      const votos = inteiro(partido.tvtn);
      const votosCadeiras = votos + inteiro(partido.tval);
      const sigla = String(partido.sg || "");
      if (nfed) {
        const federacao = federacoes.get(nfed) || {};
        const nome = String(federacao.sg || federacao.com || nfed);
        const bloco = blocos.get(`f:${nfed}`) || { nome, tipo: "federacao", partidos: [], votos: 0, votosCadeiras: 0 };
        bloco.votos += votos;
        bloco.votosCadeiras += votosCadeiras;
        if (sigla && !bloco.partidos.includes(sigla)) bloco.partidos.push(sigla);
        blocos.set(`f:${nfed}`, bloco);
      } else if (sigla) {
        blocos.set(`p:${sigla}`, { nome: sigla, tipo: "partido", partidos: [sigla], votos, votosCadeiras });
      }
    }
  }
  const lista = [...blocos.values()].sort((a, b) => b.votos - a.votos || a.nome.localeCompare(b.nome, "pt"));
  let acumulado = 0;
  for (const item of lista) {
    item.inicio = acumulado;
    acumulado += item.votos;
    item.fim = acumulado;
  }
  return lista;
}

export function interpretarApuracao(bruto, codigo = "6") {
  const cargo = cargoDeputado(bruto, codigo);
  if (!cargo) {
    const nome = String(codigo) === "7" ? "deputado estadual" : "deputado federal";
    throw new Error(`O arquivo do TSE não trouxe ${nome}.`);
  }
  const candidatos = [];
  for (const agrupamento of cargo.agr || []) {
    for (const partido of agrupamento.par || []) {
      for (const candidato of partido.cand || []) {
        candidatos.push({
          sequencial: String(candidato.sqcand || ""),
          numero: String(candidato.n || ""),
          partido: String(partido.sg || ""),
          votos: votoValido(candidato),
          percentual: String(candidato.pvap || ""),
          eleito: candidato.e === "s",
          situacao: String(candidato.st || ""),
        });
      }
    }
  }
  const qe = inteiro(cargo.qe);
  const carimbo = `${bruto.dt || ""} ${bruto.ht || ""}`.trim();
  return {
    fechada: bruto.and === "f",
    carimbo,
    secoes: bruto.s || {},
    votosNominais: inteiro(bruto.v?.vnom),
    porSequencial: new Map(candidatos.filter((item) => item.sequencial).map((item) => [item.sequencial, item])),
    porNumero: new Map(candidatos.filter((item) => item.numero).map((item) => [item.numero, item])),
    federacoes: grupos(cargo),
    quociente: {
      qe,
      vagas: inteiro(cargo.nv),
      oitenta: Math.round(qe * 0.8),
      nota:
        `Quociente eleitoral publicado pelo TSE em ${carimbo}, sem conversão de fuso. ` +
        `${inteiro(cargo.nv)} cadeiras. A marca de 80% usa esse valor publicado, sem recalcular o quociente. ` +
        "A raia soma o voto nominal válido de cada federação e de cada partido que concorre sozinho.",
    },
  };
}

function alcanca(votos, qe, percentual) {
  return votos * 100 >= qe * percentual;
}

export function cadeirasNoInstante(legendas, candidatos, qe, vagas) {
  if (qe <= 0 || vagas <= 0) return new Set();
  const porPartido = new Map(legendas.map((legenda) => [String(legenda.nome), legenda]));
  const partidoDaLegenda = new Map();
  for (const legenda of legendas) {
    for (const partido of legenda.partidos || []) partidoDaLegenda.set(String(partido), String(legenda.nome));
  }
  const fila = new Map();
  for (const candidato of candidatos) {
    const legenda = partidoDaLegenda.get(String(candidato.partido || ""));
    if (!legenda || !porPartido.has(legenda)) continue;
    const lista = fila.get(legenda) || [];
    lista.push(candidato);
    fila.set(legenda, lista);
  }
  for (const lista of fila.values()) {
    lista.sort((a, b) => (b.votos || 0) - (a.votos || 0) || String(a.id).localeCompare(String(b.id)));
  }
  const eleitos = new Set();
  const obtidas = new Map([...porPartido.keys()].map((nome) => [nome, 0]));

  function proximo(legenda, percentual) {
    for (const candidato of fila.get(legenda) || []) {
      if (eleitos.has(String(candidato.id))) continue;
      if (percentual == null || alcanca(candidato.votos || 0, qe, percentual)) return candidato;
    }
    return null;
  }

  for (const [nome, legenda] of porPartido) {
    const quociente = Math.floor((legenda.votosCadeiras || 0) / qe);
    for (let indice = 0; indice < quociente && eleitos.size < vagas; indice += 1) {
      const candidato = proximo(nome, 10);
      if (!candidato) break;
      eleitos.add(String(candidato.id));
      obtidas.set(nome, obtidas.get(nome) + 1);
    }
  }

  function escolher(percentualLegenda, percentualCandidato) {
    let melhor = null;
    for (const [nome, legenda] of porPartido) {
      const votos = legenda.votosCadeiras || 0;
      if (percentualLegenda != null && !alcanca(votos, qe, percentualLegenda)) continue;
      if (!proximo(nome, percentualCandidato)) continue;
      if (melhor == null) {
        melhor = nome;
        continue;
      }
      const votosMelhor = porPartido.get(melhor).votosCadeiras || 0;
      const atual = votos * (obtidas.get(melhor) + 1);
      const anterior = votosMelhor * (obtidas.get(nome) + 1);
      if (atual > anterior || (atual === anterior && (votos > votosMelhor || (votos === votosMelhor && nome < melhor)))) {
        melhor = nome;
      }
    }
    return melhor;
  }

  function distribuir(percentualLegenda, percentualCandidato) {
    while (eleitos.size < vagas) {
      const nome = escolher(percentualLegenda, percentualCandidato);
      if (!nome) break;
      const candidato = proximo(nome, percentualCandidato);
      if (!candidato) break;
      eleitos.add(String(candidato.id));
      obtidas.set(nome, obtidas.get(nome) + 1);
    }
  }

  distribuir(80, 20);
  distribuir(null, null);
  return eleitos;
}

export function encontrarCandidato(apuracao, pessoa) {
  if (!apuracao) return null;
  const sequencial = String(pessoa.sequencial2026 || "");
  if (sequencial && apuracao.porSequencial.has(sequencial)) return apuracao.porSequencial.get(sequencial);
  const numero = String(pessoa.numero2026 || pessoa.numero || "");
  return apuracao.porNumero.get(numero) || null;
}
