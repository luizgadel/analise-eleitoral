export const URL_APURACAO =
  "https://resultados.tse.jus.br/oficial/ele2026/6259/dados/am/am-c0006-e006259-u.json";

export const INTERVALO_APURACAO_MS = 50_000;

let pedidoAtual = null;

export function baixarApuracao() {
  if (!pedidoAtual) {
    pedidoAtual = fetch(URL_APURACAO, { cache: "no-cache" })
      .then(async (resposta) => {
        if (!resposta.ok) throw new Error("Não foi possível ler a apuração do TSE.");
        return resposta.text();
      })
      .finally(() => {
        pedidoAtual = null;
      });
  }
  return pedidoAtual;
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

function cargoDeputado(bruto) {
  const cargos = bruto?.carg || [];
  return cargos.find((item) => String(item.cd) === "6") || cargos[0];
}

function grupos(cargo) {
  const federacoes = new Map((cargo.fed || []).map((item) => [String(item.n), item]));
  const blocos = new Map();
  for (const agrupamento of cargo.agr || []) {
    for (const partido of agrupamento.par || []) {
      const nfed = String(partido.nfed || "");
      const votos = inteiro(partido.tvtn);
      const sigla = String(partido.sg || "");
      if (nfed) {
        const federacao = federacoes.get(nfed) || {};
        const nome = String(federacao.sg || federacao.com || nfed);
        const bloco = blocos.get(`f:${nfed}`) || { nome, tipo: "federacao", partidos: [], votos: 0 };
        bloco.votos += votos;
        if (sigla && !bloco.partidos.includes(sigla)) bloco.partidos.push(sigla);
        blocos.set(`f:${nfed}`, bloco);
      } else if (sigla) {
        blocos.set(`p:${sigla}`, { nome: sigla, tipo: "partido", partidos: [sigla], votos });
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

export function interpretarApuracao(bruto) {
  const cargo = cargoDeputado(bruto);
  if (!cargo) throw new Error("O arquivo do TSE não trouxe deputado federal.");
  const candidatos = [];
  for (const agrupamento of cargo.agr || []) {
    for (const partido of agrupamento.par || []) {
      for (const candidato of partido.cand || []) {
        candidatos.push({
          sequencial: String(candidato.sqcand || ""),
          numero: String(candidato.n || ""),
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
      oitenta: Math.round(qe * 0.8),
      nota:
        `Quociente eleitoral publicado pelo TSE em ${carimbo}, sem conversão de fuso. ` +
        `${inteiro(cargo.nv)} cadeiras. A marca de 80% usa esse valor publicado, sem recalcular o quociente. ` +
        "A raia soma o voto nominal válido de cada federação e de cada partido que concorre sozinho.",
    },
  };
}

export function encontrarCandidato(apuracao, pessoa) {
  if (!apuracao) return null;
  const sequencial = String(pessoa.sequencial2026 || "");
  if (sequencial && apuracao.porSequencial.has(sequencial)) return apuracao.porSequencial.get(sequencial);
  const numero = String(pessoa.numero2026 || pessoa.numero || "");
  return apuracao.porNumero.get(numero) || null;
}
