import { useEffect, useMemo, useState } from "react";
import "./estilos.css";

function iniciais(nome) {
  return nome
    .split(" ")
    .filter((parte) => parte.length > 2)
    .slice(0, 2)
    .map((parte) => parte[0])
    .join("")
    .toUpperCase();
}

function semAcento(texto) {
  return texto.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

const formatoInteiro = new Intl.NumberFormat("pt-BR");
const formatoReal = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function reais(valor) {
  if (valor == null) return "—";
  return formatoReal.format(valor);
}

function votosDe(valor) {
  if (valor == null) return "—";
  return formatoInteiro.format(valor);
}

function custoPorVoto(pessoa) {
  if (!pessoa.disputou2022 || !pessoa.votos) return null;
  return pessoa.gasto2022 / pessoa.votos;
}

const FAIXAS_GASTO = [
  { rotulo: "R$ 0", testa: (valor) => valor === 0 },
  { rotulo: "Até R$ 1 mil", testa: (valor) => valor > 0 && valor <= 1_000 },
  { rotulo: "R$ 1 mil a 10 mil", testa: (valor) => valor > 1_000 && valor <= 10_000 },
  { rotulo: "R$ 10 mil a 100 mil", testa: (valor) => valor > 10_000 && valor <= 100_000 },
  { rotulo: "R$ 100 mil a 1 milhão", testa: (valor) => valor > 100_000 && valor <= 1_000_000 },
  { rotulo: "Acima de R$ 1 milhão", testa: (valor) => valor > 1_000_000 },
];

function agrupar(pessoas) {
  const grupos = new Map();
  for (const pessoa of pessoas) {
    const lista = grupos.get(pessoa.partido) ?? [];
    lista.push(pessoa);
    grupos.set(pessoa.partido, lista);
  }
  return [...grupos.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0], "pt"));
}

function Foto({ src, nome, className }) {
  const [falhou, setFalhou] = useState(false);
  if (!src || falhou) {
    return <span className={className === "avatar" ? "iniciais avatar" : "iniciais"}>{iniciais(nome)}</span>;
  }
  return <img className={className} src={src} alt={`Foto de ${nome}`} onError={() => setFalhou(true)} />;
}

function Bandeira({ sigla, bandeiras }) {
  const [falhou, setFalhou] = useState(false);
  const src = bandeiras?.[sigla];
  if (!src || falhou) return null;
  return <img className="bandeira" src={src} alt="" onError={() => setFalhou(true)} />;
}

function Sigla({ nome, bandeiras }) {
  if (!nome) return null;
  return (
    <span className="com-bandeira">
      <Bandeira sigla={nome} bandeiras={bandeiras} />
      <span>{nome}</span>
    </span>
  );
}

function corBloco(indice) {
  return `var(--bloco-${indice % 24})`;
}

function Federacoes({ dados, bandeiras }) {
  const grupos = dados.federacoes ?? [];
  const quociente = dados.quociente;
  if (!grupos.length || !quociente) return null;
  const total = grupos[grupos.length - 1].fim || 1;
  const lugar = (valor) => `${Math.min(100, (valor / total) * 100)}%`;
  const trechoDe = (valor) => grupos.find((grupo) => valor > grupo.inicio && valor <= grupo.fim) ?? grupos[0];
  const noQe = trechoDe(quociente.qe);
  const noOitenta = trechoDe(quociente.oitenta);
  const maiorIndividual = Math.max(...grupos.map((grupo) => grupo.votos), 1);

  return (
    <section id="quociente">
      <div className="secao-titulo">
        <h2>Votos acumulados em 2022</h2>
        <p>
          A raia soma os votos, da maior votação para a menor. O gráfico de baixo mostra cada federação e cada
          partido sozinho. As linhas são o quociente eleitoral e 80% dele.
        </p>
      </div>
      <div className="raia-caixa">
        <div className="pista">
          <div className="trilho" role="img" aria-label="Acumulado de votos das federações e dos partidos, com as marcas do quociente eleitoral e de 80% do quociente">
          {grupos.map((grupo, indice) => (
            <div
              className="trecho"
              key={grupo.nome}
              style={{ width: `${(grupo.votos / total) * 100}%`, background: corBloco(indice) }}
              title={`${grupo.nome}: ${votosDe(grupo.votos)} votos nominais`}
            />
          ))}
          </div>
          <span className="marco oitenta" style={{ left: lugar(quociente.oitenta) }}>
            <span>
              80% do QE
              <strong>{votosDe(quociente.oitenta)}</strong>
            </span>
          </span>
          <span className="marco qe" style={{ left: lugar(quociente.qe) }}>
            <span>
              QE
              <strong>{votosDe(quociente.qe)}</strong>
            </span>
          </span>
        </div>
        <div className="escala-raia">
          <span>0</span>
          <span>{votosDe(total)} votos nominais</span>
        </div>
        <p className="miudo nota">
          O quociente cai em {noQe.nome}. Os 80% caem em {noOitenta.nome}. {quociente.nota}
        </p>
      </div>
      <div className="secao-titulo sub">
        <h2>Votação de cada bloco</h2>
        <p>A largura da barra é o voto nominal daquele partido ou daquela federação.</p>
      </div>
      <div className="grafico-individual">
        <span />
        <div className="legenda-cortes">
          <span className="corte-legenda oitenta" style={{ left: `${(quociente.oitenta / maiorIndividual) * 100}%` }}>
            80% do QE
            <strong>{votosDe(quociente.oitenta)}</strong>
          </span>
          <span className="corte-legenda qe" style={{ left: `${(quociente.qe / maiorIndividual) * 100}%` }}>
            QE
            <strong>{votosDe(quociente.qe)}</strong>
          </span>
        </div>
        <span />
        {grupos.map((grupo, indice) => (
          <div className="linha-barra" key={`barra-${grupo.nome}`}>
            <strong>{grupo.nome}</strong>
            <div className="trilha-barra">
              <span
                className="enchimento"
                style={{
                  width: `${(grupo.votos / maiorIndividual) * 100}%`,
                  background: corBloco(indice),
                }}
              />
              <i className="corte oitenta" style={{ left: `${(quociente.oitenta / maiorIndividual) * 100}%` }} />
              <i className="corte qe" style={{ left: `${(quociente.qe / maiorIndividual) * 100}%` }} />
            </div>
            <span className="nums">{votosDe(grupo.votos)}</span>
          </div>
        ))}
      </div>
      <div className="federacoes">
        {grupos.map((grupo, indice) => {
          const passouQe = grupo.votos >= quociente.qe;
          const passouOitenta = grupo.votos >= quociente.oitenta;
          const situacao = passouQe ? "Passou do quociente" : passouOitenta ? "Passou de 80% do quociente" : "Abaixo de 80% do quociente";
          return (
            <article className="federacao" key={grupo.nome}>
              <span className="amostra" style={{ background: corBloco(indice) }} />
              <div>
                <strong>{grupo.nome}</strong>
                <span className="partido-linha">
                  {grupo.partidos.map((partido) => (
                    <Sigla key={partido} nome={partido} bandeiras={bandeiras} />
                  ))}
                </span>
              </div>
              <span className="nums">{votosDe(grupo.votos)}</span>
              <span className="nums miudo">acumulado {votosDe(grupo.fim)}</span>
              <span className={passouQe ? "etiqueta dentro" : "etiqueta fora"}>{situacao}</span>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function Lista({ titulo, pessoas, bandeiras, sentido }) {
  const grupos = agrupar(pessoas);
  const total = pessoas.filter((pessoa) => !pessoa.troca).length;
  return (
    <div className="coluna">
      <h3>
        {titulo} <span style={{ color: "var(--tinta-suave)" }}>{total}</span>
      </h3>
      {grupos.map(([partido, lista]) => (
        <div className="grupo" key={partido}>
          <header>
            <Sigla nome={partido} bandeiras={bandeiras} />
            <span>{lista.filter((pessoa) => !pessoa.troca).length}</span>
          </header>
          <div className="pessoas">
            {lista.map((pessoa) => (
              <span className={pessoa.troca ? "pessoa troca" : "pessoa"} key={`${pessoa.troca ? "troca" : "fixo"}-${pessoa.nome}`}>
                <Foto src={pessoa.foto} nome={pessoa.nomeUrna} />
                <span>
                  {pessoa.nomeUrna}
                  {pessoa.numero ? ` · ${pessoa.numero}` : ""}
                  {pessoa.troca && (
                    <small>
                      {sentido === "entrada" ? "veio de " : "trocou para "}
                      {pessoa.outroPartido}
                    </small>
                  )}
                </span>
              </span>
            ))}
          </div>
        </div>
      ))}
      {pessoas.length === 0 && <p>Nenhuma pessoa com esse nome.</p>}
    </div>
  );
}

export default function App() {
  const [dados, setDados] = useState(null);
  const [bandeiras, setBandeiras] = useState({});
  const [erro, setErro] = useState("");
  const [busca, setBusca] = useState("");
  const [buscaDesempenho, setBuscaDesempenho] = useState("");
  const [ordem, setOrdem] = useState("votos");

  useEffect(() => {
    Promise.all([
      fetch("/dados/amazonas.json", { cache: "no-store" }).then((resposta) => {
        if (!resposta.ok) throw new Error("Não foi possível carregar os dados.");
        return resposta.json();
      }),
      fetch("/bandeiras/mapa.json", { cache: "no-store" }).then((resposta) => (resposta.ok ? resposta.json() : {})),
    ])
      .then(([quadro, mapa]) => {
        setDados(quadro);
        setBandeiras(mapa);
      })
      .catch((falha) => setErro(falha.message));
  }, []);

  const filtrados = useMemo(() => {
    if (!dados) return { sairam: [], entraram: [] };
    const termo = semAcento(busca.trim());
    const cabe = (pessoa) =>
      !termo ||
      semAcento(`${pessoa.nomeUrna} ${pessoa.nome} ${pessoa.partido} ${pessoa.outroPartido || ""}`).includes(termo);
    const fotoPorNome = new Map(
      dados.desempenho
        .filter((pessoa) => pessoa.disputou2022)
        .map((pessoa) => [semAcento(pessoa.nomeUrna), pessoa]),
    );
    const trocaNoPartido = (partidoDe, outroPartido) =>
      dados.trocas.map((pessoa) => {
        const origem = fotoPorNome.get(semAcento(pessoa.nomeUrna));
        return {
          nome: pessoa.nome,
          nomeUrna: pessoa.nomeUrna,
          partido: pessoa[partidoDe],
          outroPartido: pessoa[outroPartido],
          numero: partidoDe === "partido2022" ? origem?.numero || "" : "",
          foto: origem?.foto || "",
          troca: true,
        };
      });
    return {
      sairam: [...dados.sairam, ...trocaNoPartido("partido2022", "partido2026")].filter(cabe),
      entraram: [...dados.entraram, ...trocaNoPartido("partido2026", "partido2022")].filter(cabe),
    };
  }, [busca, dados]);

  const desempenho = useMemo(() => {
    if (!dados) return [];
    const termo = semAcento(buscaDesempenho.trim());
    const valor = (pessoa) => {
      if (ordem === "gasto2022") return pessoa.gasto2022 ?? -1;
      if (ordem === "gasto2026") return pessoa.gasto2026 ?? -1;
      if (ordem === "custo") return custoPorVoto(pessoa) ?? -1;
      return pessoa.votos ?? -1;
    };
    return dados.desempenho
      .filter(
        (pessoa) =>
          !termo || semAcento(`${pessoa.nomeUrna} ${pessoa.nome} ${pessoa.partido}`).includes(termo),
      )
      .sort((a, b) => valor(b) - valor(a) || a.nomeUrna.localeCompare(b.nomeUrna, "pt"));
  }, [buscaDesempenho, dados, ordem]);

  const maioresGastos = useMemo(() => {
    if (!dados) return [];
    return dados.desempenho
      .filter((pessoa) => pessoa.disputou2022)
      .sort((a, b) => b.gasto2022 - a.gasto2022 || (b.votos || 0) - (a.votos || 0))
      .slice(0, 50);
  }, [dados]);

  const faixasGasto = useMemo(() => {
    if (!dados) return [];
    const campanhas = dados.desempenho.filter((pessoa) => pessoa.disputou2022);
    return FAIXAS_GASTO.map((faixa) => ({
      rotulo: faixa.rotulo,
      quantidade: campanhas.filter((pessoa) => faixa.testa(pessoa.gasto2022 || 0)).length,
    }));
  }, [dados]);

  const antecipado = useMemo(() => {
    if (!dados) return null;
    const passo = 4;
    const faixas = Array.from({ length: 100 / passo }, (_, indice) => ({
      rotulo: `${indice * passo}–${(indice + 1) * passo}%`,
      quantidade: 0,
    }));
    let semDespesa = 0;
    let acima = 0;
    for (const pessoa of dados.desempenho) {
      if (!pessoa.disputou2022) continue;
      const final = pessoa.gasto2022 || 0;
      if (final <= 0) {
        semDespesa += 1;
        continue;
      }
      const percentual = ((pessoa.gastoAteSemana || 0) / final) * 100;
      if (percentual > 100) {
        acima += 1;
        continue;
      }
      faixas[Math.min(faixas.length - 1, Math.floor(percentual / passo))].quantidade += 1;
    }
    return { faixas, semDespesa, acima };
  }, [dados]);

  if (erro) return <p className="estado">{erro}</p>;
  if (!dados) return <p className="estado">Carregando o Amazonas…</p>;

  const maior = Math.max(...dados.partidos.flatMap((item) => [item.candidatos2022, item.candidatos2026]), 1);
  const maiorVoto = Math.max(...dados.desempenho.map((pessoa) => pessoa.votos || 0), 1);
  const maiorGasto = Math.max(
    ...dados.publicidadePartidos.flatMap((item) => [item.gasto2022, item.gasto2026]),
    1,
  );
  const colunasAntecipado = [
    ...antecipado.faixas,
    ...(antecipado.acima ? [{ rotulo: "Acima de 100%", quantidade: antecipado.acima }] : []),
  ];
  const tetoAntecipado = Math.max(...colunasAntecipado.map((item) => item.quantidade), 1);

  return (
    <main className="pagina">
      <header className="topo">
        <div>
          <p className="selo">Deputado federal · Amazonas</p>
          <h1>Quem disputou, quem senta e quem volta em 2026.</h1>
        </div>
        <p className="intro">
          Candidaturas aptas a deputado federal na eleição ordinária. Em 2026 a situação ainda não veio
          preenchida pelo TSE, então a lista reúne quem está no cadastro oficial do estado.
        </p>
      </header>

      <nav className="nav">
        <a href="#eleitos">Eleitos</a>
        <a href="#quociente">Quociente</a>
        <a href="#maiores">50 maiores gastos</a>
        <a href="#antecipado">Uma semana antes</a>
        <a href="#votos">Votos e gastos</a>
        <a href="#partidos">Por partido</a>
        <a href="#trocas">Trocas de partido</a>
        <a href="#movimento">Quem saiu e quem entrou</a>
      </nav>

      <section className="numeros" aria-label="Resumo">
        <article className="numero">
          <strong>{dados.totais.candidatos2022}</strong>
          <span>candidaturas em 2022</span>
        </article>
        <article className="numero">
          <strong>{dados.totais.eleitos2022}</strong>
          <span>eleitos, todos ainda na Câmara</span>
        </article>
        <article className="numero">
          <strong>{dados.totais.candidatos2026}</strong>
          <span>candidaturas em 2026</span>
        </article>
        <article className="numero">
          <strong>{dados.totais.continuam}</strong>
          <span>repetem a disputa</span>
        </article>
      </section>

      <section id="eleitos">
        <div className="secao-titulo">
          <h2>Eleitos em 2022</h2>
          <p>Oito cadeiras. A foto é a oficial da Câmara. O partido de baixo é o de hoje, quando mudou desde a eleição.</p>
        </div>
        <div className="grade-eleitos">
          {dados.eleitos.map((pessoa) => (
            <article className="eleito" key={pessoa.numero + pessoa.nome}>
              <Foto className="avatar" src={pessoa.foto} nome={pessoa.nomeUrna} />
              <div>
                <h3>{pessoa.nomeUrna}</h3>
                <p className="voto-grande">
                  {votosDe(pessoa.votos)} <span>votos</span>
                </p>
                <p className="miudo">
                  {reais(pessoa.gasto2022)} em despesas da campanha
                  {pessoa.votos ? ` · ${reais(pessoa.gasto2022 / pessoa.votos)} por voto` : ""}
                </p>
                {pessoa.concorre2026 && pessoa.gasto2026 > 0 && (
                  <p className="miudo">{reais(pessoa.gasto2026)} contratados em 2026</p>
                )}
                <p className="partido-linha">
                  <Sigla nome={pessoa.partido} bandeiras={bandeiras} />
                  {pessoa.partidoAtual !== pessoa.partido && (
                    <>
                      na eleição, hoje <Sigla nome={pessoa.partidoAtual} bandeiras={bandeiras} />
                    </>
                  )}
                  <span>· {pessoa.numero}</span>
                </p>
                <p className="partido-linha">{pessoa.resultado}</p>
                <span className={pessoa.concorre2026 ? "etiqueta dentro" : "etiqueta fora"}>
                  {pessoa.concorre2026 ? (
                    <>
                      Concorre em 2026 pelo <Sigla nome={pessoa.partido2026} bandeiras={bandeiras} />
                    </>
                  ) : (
                    "Não concorre em 2026"
                  )}
                </span>
              </div>
            </article>
          ))}
        </div>
        {dados.foraDaDisputa.map((pessoa) => (
          <aside className="aviso" key={pessoa.nome}>
            <Foto src={pessoa.foto} nome={pessoa.nome} />
            <div>
              <h3>{pessoa.nome} não está na disputa de 2026</h3>
              <p>
                É o único deputado do Amazonas em exercício, hoje no{" "}
                <Sigla nome={pessoa.partido} bandeiras={bandeiras} />, que não aparece entre os candidatos a
                deputado federal neste ano.
              </p>
            </div>
          </aside>
        ))}
      </section>

      <Federacoes dados={dados} bandeiras={bandeiras} />

      <section id="votos">
        <div className="secao-titulo">
          <h2>Votos de 2022 e gastos da campanha</h2>
          <p>
            O voto nominal fica ao lado de todas as despesas contratadas, não só publicidade. Em 2022 dá para ver
            quanto a campanha custou por voto. Em 2026 o número é o que já foi contratado.
          </p>
        </div>
        <div className="numeros tres">
          <article className="numero">
            <strong>{votosDe(dados.totais.votos2022)}</strong>
            <span>votos nominais em 2022</span>
          </article>
          <article className="numero">
            <strong>{reais(dados.totais.publicidade2022)}</strong>
            <span>despesas contratadas em 2022</span>
          </article>
          <article className="numero">
            <strong>{reais(dados.totais.publicidade2026)}</strong>
            <span>despesas contratadas em 2026, até 03/09</span>
          </article>
        </div>
        <p className="miudo nota">{dados.notaVotos} {dados.notaPublicidade2022} {dados.notaPublicidade2026}</p>

        <div className="secao-titulo sub" id="maiores">
          <h2>Os 50 maiores gastos em 2022</h2>
          <p>Despesa contratada total, da maior campanha para a menor.</p>
        </div>
        <div className="ranking maiores">
          <div className="linha-voto cabeca curta">
            <span />
            <span>Candidatura</span>
            <span>Votos</span>
            <span>Gastos da campanha</span>
          </div>
          {maioresGastos.map((pessoa, indice) => (
            <div className={pessoa.eleito ? "linha-voto curta eleita" : "linha-voto curta"} key={`gasto-${pessoa.numero}-${pessoa.nome}`}>
              <span className="posicao">{indice + 1}</span>
              <div className="quem">
                {pessoa.foto && <Foto className="mini" src={pessoa.foto} nome={pessoa.nomeUrna} />}
                <div>
                  <strong>{pessoa.nomeUrna}</strong>
                  <span className="partido-linha">
                    <Sigla nome={pessoa.partido} bandeiras={bandeiras} />
                    {pessoa.eleito && <span className="etiqueta dentro">Eleito</span>}
                  </span>
                </div>
              </div>
              <span className="nums">{votosDe(pessoa.votos)}</span>
              <span className="nums">{reais(pessoa.gasto2022)}</span>
            </div>
          ))}
        </div>

        <div className="secao-titulo sub">
          <h2>Candidatos por faixa de gasto</h2>
          <p>
            Cada faixa é dez vezes maior que a anterior. Uma escala de R$ 1 mil em R$ 1 mil, de zero até mais de
            R$ 3 milhões, deixaria a maior parte das colunas vazia.
          </p>
        </div>
        <div className="partidos faixas">
          {faixasGasto.map((faixa) => {
            const teto = Math.max(...faixasGasto.map((item) => item.quantidade), 1);
            return (
              <div className="linha-partido larga" key={faixa.rotulo}>
                <span className="sigla faixa-nome">{faixa.rotulo}</span>
                <div className="trilhos">
                  <div className="barra a" style={{ width: faixa.quantidade ? `${(faixa.quantidade / teto) * 100}%` : 0 }} />
                </div>
                <span className="nums">{faixa.quantidade}</span>
              </div>
            );
          })}
        </div>

        <div className="secao-titulo sub" id="antecipado">
          <h2>Gasto até uma semana antes da votação</h2>
          <p>
            Cada coluna conta quantos candidatos de 2022 já tinham contratado aquela faixa de 4 pontos
            percentuais do gasto final em 25 de setembro, uma semana antes do primeiro turno.
          </p>
        </div>
        <p className="miudo nota">{dados.notaGastoAntecipado}</p>
        <div className="histograma-caixa">
          <div
            className="histograma"
            style={{ gridTemplateColumns: `repeat(${colunasAntecipado.length}, minmax(0, 1fr))` }}
            role="img"
            aria-label={colunasAntecipado.map((faixa) => `${faixa.rotulo}: ${faixa.quantidade} candidatos`).join(". ")}
          >
            {colunasAntecipado.map((faixa) => (
              <div className="coluna-dezena" key={faixa.rotulo}>
                <span className="qtd">{faixa.quantidade}</span>
                <div className="eixo-qtd" aria-hidden="true">
                  <div
                    className="enchimento"
                    style={{ height: faixa.quantidade ? `${(faixa.quantidade / tetoAntecipado) * 100}%` : 0 }}
                  />
                </div>
                <span className="faixa-pct">{faixa.rotulo}</span>
              </div>
            ))}
          </div>
        </div>
        {antecipado.semDespesa > 0 && (
          <p className="miudo nota">
            {antecipado.semDespesa} candidaturas fecharam sem despesa contratada e ficam fora das colunas, porque não há porcentagem.
          </p>
        )}

        <div className="ordens" role="group" aria-label="Ordenar candidaturas">
          {[
            ["votos", "Mais votos"],
            ["gasto2022", "Maior gasto em 2022"],
            ["custo", "Maior custo por voto"],
            ["gasto2026", "Maior gasto em 2026"],
          ].map(([id, rotulo]) => (
            <button key={id} type="button" className={ordem === id ? "ativo" : ""} onClick={() => setOrdem(id)}>
              {rotulo}
            </button>
          ))}
        </div>
        <input
          className="busca"
          value={buscaDesempenho}
          onChange={(evento) => setBuscaDesempenho(evento.target.value)}
          placeholder="Buscar candidatura"
          aria-label="Buscar candidatura na votação"
        />
        <div className="ranking">
          <div className="linha-voto cabeca">
            <span />
            <span>Candidatura</span>
            <span>Votos em 2022</span>
            <span>Gastos 2022</span>
            <span>Por voto</span>
            <span>Gastos 2026</span>
          </div>
          {desempenho.map((pessoa, indice) => (
            <div className={pessoa.eleito ? "linha-voto eleita" : "linha-voto"} key={`${pessoa.numero}-${pessoa.nome}`}>
              <span className="posicao">{indice + 1}</span>
              <div className="quem">
                {pessoa.foto && <Foto className="mini" src={pessoa.foto} nome={pessoa.nomeUrna} />}
                <div>
                  <strong>{pessoa.nomeUrna}</strong>
                  <span className="partido-linha">
                    <Sigla nome={pessoa.partido} bandeiras={bandeiras} />
                    {pessoa.eleito && <span className="etiqueta dentro">Eleito</span>}
                    {!pessoa.disputou2022 && <span className="etiqueta">Só em 2026</span>}
                  </span>
                  <div className="trilho-voto" aria-hidden="true">
                    <div
                      className="barra a"
                      style={{ width: pessoa.votos ? `${(pessoa.votos / maiorVoto) * 100}%` : 0 }}
                    />
                  </div>
                </div>
              </div>
              <span className="nums">{votosDe(pessoa.votos)}</span>
              <span className="nums">{reais(pessoa.gasto2022)}</span>
              <span className="nums">{reais(custoPorVoto(pessoa))}</span>
              <span className="nums">{reais(pessoa.gasto2026)}</span>
            </div>
          ))}
          {desempenho.length === 0 && <p className="miudo nota">Nenhuma candidatura com esse nome.</p>}
        </div>
        <div className="secao-titulo sub">
          <h2>Gastos por partido</h2>
          <div className="legenda">
            <span><i className="ponto a" /> 2022</span>
            <span><i className="ponto b" /> 2026</span>
          </div>
        </div>
        <div className="partidos">
          {dados.publicidadePartidos.map((item) => {
            return (
              <div className="linha-partido larga" key={item.partido}>
                <Sigla nome={item.partido} bandeiras={bandeiras} />
                <div className="trilhos">
                  <div className="barra a" style={{ width: item.gasto2022 ? `${(item.gasto2022 / maiorGasto) * 100}%` : 0 }} />
                  <div className="barra b" style={{ width: item.gasto2026 ? `${(item.gasto2026 / maiorGasto) * 100}%` : 0 }} />
                </div>
                <span className="nums dinheiro">
                  {reais(item.gasto2022)}
                  <br />
                  {reais(item.gasto2026)}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      <section id="partidos">
        <div className="secao-titulo">
          <h2>Candidaturas por partido</h2>
          <div className="legenda">
            <span><i className="ponto a" /> 2022</span>
            <span><i className="ponto b" /> 2026</span>
          </div>
        </div>
        <div className="partidos">
          {dados.partidos.map((item) => (
            <div className="linha-partido" key={item.partido}>
              <Sigla nome={item.partido} bandeiras={bandeiras} />
              <div className="trilhos">
                <div className="barra a" style={{ width: item.candidatos2022 ? `${(item.candidatos2022 / maior) * 100}%` : 0 }} />
                <div className="barra b" style={{ width: item.candidatos2026 ? `${(item.candidatos2026 / maior) * 100}%` : 0 }} />
              </div>
              <span className="nums">
                {item.candidatos2022} · {item.candidatos2026}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section id="trocas">
        <div className="secao-titulo">
          <h2>Quem continua e trocou de partido</h2>
          <p>{dados.totais.trocaramPartido} pessoas disputaram os dois anos com siglas diferentes.</p>
        </div>
        <div className="trocas">
          {dados.trocas.map((pessoa) => (
            <article className="troca" key={pessoa.nome}>
              <strong>{pessoa.nomeUrna}</strong>
              <span className="partido-linha">
                <Sigla nome={pessoa.partido2022} bandeiras={bandeiras} />
                <span aria-hidden="true">→</span>
                <Sigla nome={pessoa.partido2026} bandeiras={bandeiras} />
              </span>
            </article>
          ))}
        </div>
      </section>

      <section id="movimento">
        <div className="secao-titulo">
          <h2>Quem saiu e quem entrou</h2>
          <p>
            {dados.totais.sairam} deixaram a disputa e {dados.totais.entraram} aparecem só em 2026. Quem trocou de
            partido aparece no partido de saída e no partido novo, fora dessas contas. As fotos novas são do TSE.
          </p>
        </div>
        <input
          className="busca"
          value={busca}
          onChange={(evento) => setBusca(evento.target.value)}
          placeholder="Buscar por nome ou partido"
          aria-label="Buscar por nome ou partido"
        />
        <div className="colunas">
          <Lista titulo="Saíram" pessoas={filtrados.sairam} bandeiras={bandeiras} sentido="saida" />
          <Lista titulo="Entraram" pessoas={filtrados.entraram} bandeiras={bandeiras} sentido="entrada" />
        </div>
      </section>

      <footer className="rodape">
        <p>
          Fontes: candidaturas do TSE e deputados em exercício da Câmara. {dados.notaEleitos} {dados.notaFotos2026}
        </p>
      </footer>
    </main>
  );
}
