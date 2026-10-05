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
    const nomes = { 5: "senador", 7: "deputado estadual" };
    const nome = nomes[String(codigo)] || "deputado federal";
    throw new Error(`O arquivo do TSE não trouxe ${nome}.`);
  }
  const uf = String(bruto.cdabr || "").toUpperCase();
  const candidatos = [];
  for (const agrupamento of cargo.agr || []) {
    for (const partido of agrupamento.par || []) {
      for (const candidato of partido.cand || []) {
        candidatos.push({
          sequencial: String(candidato.sqcand || ""),
          numero: String(candidato.n || ""),
          uf,
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
    uf,
    porSequencial: new Map(candidatos.filter((item) => item.sequencial).map((item) => [item.sequencial, item])),
    porNumero: new Map(
      candidatos
        .filter((item) => item.numero)
        .map((item) => [item.uf ? `${item.uf}:${item.numero}` : item.numero, item]),
    ),
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

export function cadeirasMajoritarias(candidatos, vagas, vagasPorUf) {
  if (vagasPorUf && Object.keys(vagasPorUf).length) {
    const eleitos = new Set();
    const grupos = new Map();
    for (const pessoa of candidatos) {
      const uf = String(pessoa.uf || "");
      const lista = grupos.get(uf) || [];
      lista.push(pessoa);
      grupos.set(uf, lista);
    }
    for (const [uf, lista] of grupos) {
      for (const id of cadeirasMajoritarias(lista, vagasPorUf[uf] || vagas)) eleitos.add(id);
    }
    return eleitos;
  }
  if (vagas <= 0) return new Set();
  return new Set(
    [...candidatos]
      .filter((pessoa) => (pessoa.votos || 0) > 0)
      .sort((a, b) => (b.votos || 0) - (a.votos || 0) || String(a.id).localeCompare(String(b.id)))
      .slice(0, vagas)
      .map((pessoa) => String(pessoa.id)),
  );
}

export function juntarApuracoes(partes) {
  const porSequencial = new Map();
  const porNumero = new Map();
  const blocos = new Map();
  const vagasPorUf = {};
  let vagas = 0;
  let votosNominais = 0;
  let secoesApuradas = 0;
  let secoesTotais = 0;
  let fechada = true;
  let carimbo = "";
  for (const parte of partes) {
    fechada = fechada && Boolean(parte.fechada);
    if ((parte.carimbo || "") > carimbo) carimbo = parte.carimbo || "";
    const lugares = parte.quociente?.vagas || 0;
    vagas += lugares;
    votosNominais += parte.votosNominais || 0;
    secoesApuradas += inteiro(parte.secoes?.st);
    secoesTotais += inteiro(parte.secoes?.ts);
    if (parte.uf) vagasPorUf[parte.uf] = lugares;
    for (const candidato of parte.porSequencial.values()) {
      if (candidato.sequencial) porSequencial.set(candidato.sequencial, candidato);
      if (candidato.numero) porNumero.set(candidato.uf ? `${candidato.uf}:${candidato.numero}` : candidato.numero, candidato);
    }
    for (const grupo of parte.federacoes || []) {
      const atual = blocos.get(grupo.nome) || {
        nome: grupo.nome,
        tipo: grupo.tipo,
        partidos: [],
        votos: 0,
        votosCadeiras: 0,
      };
      atual.votos += grupo.votos || 0;
      atual.votosCadeiras += grupo.votosCadeiras || 0;
      for (const partido of grupo.partidos || []) {
        if (!atual.partidos.includes(partido)) atual.partidos.push(partido);
      }
      blocos.set(grupo.nome, atual);
    }
  }
  const federacoes = [...blocos.values()].sort((a, b) => b.votos - a.votos || a.nome.localeCompare(b.nome, "pt"));
  let acumulado = 0;
  for (const item of federacoes) {
    item.inicio = acumulado;
    acumulado += item.votos;
    item.fim = acumulado;
  }
  return {
    fechada,
    carimbo,
    votosNominais,
    secoes: secoesTotais
      ? {
          st: String(secoesApuradas),
          ts: String(secoesTotais),
          pst: String(Math.round((secoesApuradas / secoesTotais) * 1000) / 10).replace(".", ","),
        }
      : {},
    uf: "BR",
    vagasPorUf,
    porSequencial,
    porNumero,
    federacoes,
    quociente: {
      qe: 0,
      vagas,
      oitenta: 0,
      nota:
        `Apuração de senador nos estados. O carimbo mais recente é ${carimbo}, sem conversão de fuso. ` +
        "Cada estado elege os mais votados. A raia soma o voto nominal do partido no país.",
    },
  };
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
  const uf = String(pessoa.uf || "");
  if (uf && apuracao.porNumero.has(`${uf}:${numero}`)) return apuracao.porNumero.get(`${uf}:${numero}`);
  return apuracao.porNumero.get(numero) || null;
}
