const team = [
  ['Ana Luisa', 'Desenvolvimento', 'member1.jpg'],
  ['Davi Souza', 'Inteligência artificial', 'member2.png'],
  ['Marcos Menezes', 'Desenvolvimento full-stack', 'member3.png'],
  ['Rafael Marinato', 'Experiência e interface', 'member4.png'],
]

const steps = [
  ['01', 'Captura', 'A câmera registra o ambiente monitorado.'],
  ['02', 'Análise', 'O modelo identifica presença e ausência de EPIs.'],
  ['03', 'Alerta', 'A ocorrência é sinalizada para ação imediata.'],
  ['04', 'Evidência', 'Dados e capturas formam o histórico operacional.'],
]

/** Conta a missão, o fluxo técnico e apresenta a equipe do projeto. */
export default function About() {
  return (
    <>
      <section className="about-hero"><div><span className="eyebrow">SAFETYLENS · NOSSA MISSÃO</span><h2>Transformar câmeras comuns em aliadas da segurança industrial.</h2><p>Visão computacional para monitorar equipamentos de proteção, reduzir exposição ao risco e apoiar decisões preventivas.</p></div></section>
      <section className="steps-grid">{steps.map(([number, title, text]) => <article key={number}><span>{number}</span><h3>{title}</h3><p>{text}</p></article>)}</section>
      <section className="editorial-row technology"><div><span className="eyebrow">TECNOLOGIA</span><h2>Construído para operar localmente.</h2></div><div className="technology-list"><p><strong>YOLO + PyTorch</strong><span>Detecção multiclasse em tempo real</span></p><p><strong>OpenCV</strong><span>Captura e processamento de vídeo</span></p><p><strong>React + Flask</strong><span>Experiência web e API de dados</span></p><p><strong>SQLite</strong><span>Histórico local e portátil</span></p></div></section>
      <section className="panel section-panel"><div className="panel-heading"><div><span className="eyebrow">TIME SAFETYLENS</span><h2>Quem constrói essa visão</h2></div></div><div className="team-grid">{team.map(([name, role, image]) => <article key={name}><img src={`/img/${image}`} alt={`Retrato de ${name}`} /><h3>{name}</h3><p>{role}</p></article>)}</div></section>
    </>
  )
}
