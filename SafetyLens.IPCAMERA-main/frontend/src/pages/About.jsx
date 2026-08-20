/** Conta a história pessoal do SafetyLens, da ideia inicial à fase open source. */
export default function About() {
  return (
    <div className="about-story">
      <section className="about-hero">
        <div className="about-shape about-shape--orb" aria-hidden="true" />
        <div className="about-shape about-shape--ring" aria-hidden="true" />
        <div className="about-shape about-shape--bar" aria-hidden="true" />
        <div className="about-hero__content">
          <span className="eyebrow">SOBRE O SAFETYLENS</span>
          <h2>Uma ideia sobre segurança que encontrou seu caminho na visão computacional.</h2>
          <p>O SafetyLens começou antes de ter nome, código ou qualquer modelo de inteligência artificial treinado.</p>
        </div>
        <span className="about-hero__index" aria-hidden="true">01 — 05</span>
      </section>

      <section className="story-layout" aria-labelledby="story-title">
        <aside className="story-index">
          <span className="eyebrow">A HISTÓRIA</span>
          <h2 id="story-title">De projeto final a projeto de vida.</h2>
          <ol>
            <li>O começo</li>
            <li>A competição</li>
            <li>A pausa</li>
            <li>O retorno</li>
            <li>O futuro</li>
          </ol>
        </aside>

        <article className="story-content">
          <section className="story-chapter">
            <span>01</span>
            <h3>O começo</h3>
            <p>No início do meu curso técnico em Desenvolvimento de Sistemas no SENAI, eu já pensava no que gostaria de construir como projeto final. Eu queria desenvolver algo relacionado à segurança e já tinha em mente utilizar inteligência artificial, mas ainda não sabia exatamente de que forma transformar isso em um produto.</p>
            <p>Foi então que, durante uma conversa, o Rafael sugeriu utilizar visão computacional. Essa ideia acabou sendo a peça que faltava. A partir dali, começamos a pensar em como uma câmera poderia deixar de servir apenas para monitoramento e passar a interpretar o ambiente ao seu redor utilizando inteligência artificial.</p>
            <p>Foi dessa combinação que nasceu o SafetyLens: uma solução baseada em inteligência artificial e visão computacional para identificar automaticamente se trabalhadores estão utilizando corretamente seus Equipamentos de Proteção Individual.</p>
            <p>A ideia ganhou forma quando nos reunimos em um grupo de quatro pessoas: eu, Ana, Davi e Rafael. Cada um participou da construção do projeto em diferentes momentos, mas faço questão de destacar especialmente o Rafael, não apenas pela colaboração durante o desenvolvimento, mas também porque foi dele a sugestão de utilizar visão computacional, que acabou sendo fundamental para definir o caminho que o projeto seguiria.</p>
          </section>

          <section className="story-chapter story-chapter--featured">
            <div className="about-shape about-shape--spark" aria-hidden="true" />
            <span>02</span>
            <h3>Dois meses. Uma competição. Um segundo lugar.</h3>
            <p>Pouco tempo depois surgiu a oportunidade de participar do Inova SENAI. O desafio era grande: fomos avisados sobre a competição quando faltavam aproximadamente dois meses para o evento.</p>
            <p>Mesmo com pouco tempo, nos desdobramos para transformar uma ideia ainda em desenvolvimento em algo que pudesse ser apresentado. Foram semanas de pesquisa, programação, testes, erros, ajustes e muita correria até conseguirmos levar o projeto para Serra, no Espírito Santo.</p>
            <strong>No final, conquistamos o segundo lugar estadual.</strong>
            <p>Para mim, aquele resultado mostrou que a ideia tinha potencial para ser muito maior do que apenas um trabalho de conclusão de curso.</p>
          </section>

          <section className="story-chapter">
            <span>03</span>
            <h3>Por mais de um ano.</h3>
            <p>Com o fim do SENAI, porém, o projeto acabou ficando parado. Existia a expectativa de continuidade e de participação em uma etapa nacional, mas isso não aconteceu como havia sido combinado. Aos poucos, o entusiasmo diminuiu e o SafetyLens acabou sendo deixado de lado.</p>
            <p className="story-pause">Por mais de um ano.</p>
            <p>Depois desse tempo, decidi voltar.</p>
          </section>

          <section className="story-chapter">
            <span>04</span>
            <h3>Um novo capítulo</h3>
            <p>Dessa vez, não como um trabalho acadêmico, nem como algo que precisava ser entregue para receber uma nota ou participar de uma competição. Decidi continuar porque percebi que ainda havia muito que eu queria aprender através daquele projeto.</p>
            <p>Passei então a reconstruir o SafetyLens com outra mentalidade: estudar inteligência artificial de forma mais profunda, melhorar a arquitetura do sistema, trabalhar com datasets maiores, treinar novos modelos, experimentar tecnologias diferentes e transformar um protótipo acadêmico em um projeto de software de verdade.</p>
            <p>Essa nova fase é uma continuação do trabalho que começou com aquele grupo, mas também representa um novo capítulo do projeto, agora desenvolvido e mantido por mim.</p>
            <blockquote>Hoje, o SafetyLens é também parte da minha própria trajetória como desenvolvedor.</blockquote>
          </section>

          <section className="story-chapter">
            <span>05</span>
            <h3>Aberto para chegar mais longe</h3>
            <p>Minha intenção é mantê-lo open source para que outras pessoas possam estudar o projeto, modificar o código, treinar seus próprios modelos e talvez utilizar alguma parte dele para criar soluções ainda melhores.</p>
            <p>Talvez alguém encontre este repositório procurando aprender visão computacional. Talvez outra pessoa queira desenvolver uma solução de segurança para uma empresa. Talvez alguém simplesmente veja o projeto e tenha uma ideia completamente diferente.</p>
            <p>Se isso acontecer, o SafetyLens já terá cumprido uma parte importante do seu propósito.</p>
            <p>O projeto começou como uma ideia construída em grupo para terminar um curso.</p>
            <p>Hoje, continuo desenvolvendo porque quero descobrir até onde essa ideia pode chegar.</p>
          </section>
        </article>
      </section>

      <section className="about-closing">
        <div className="about-shape about-shape--closing" aria-hidden="true" />
        <div className="about-signature">
          <span>—</span>
          <strong>Marcos Menezzes</strong>
          <small>Criador e mantenedor do SafetyLens</small>
        </div>
        <div className="acknowledgements">
          <span className="eyebrow">AGRADECIMENTOS</span>
          <h2>Uma história construída por mais de uma pessoa.</h2>
          <p>O SafetyLens não teria chegado até aqui sem as pessoas que participaram da sua primeira fase.</p>
          <p>Meu agradecimento à <strong>Ana</strong>, ao <strong>Davi</strong> e, especialmente, ao <strong>Rafael</strong>, que teve uma participação muito importante no desenvolvimento do projeto e foi uma das pessoas que mais colaborou comigo durante a construção da versão original apresentada no Inova SENAI.</p>
          <p>Também faço questão de registrar que foi o Rafael quem sugeriu o uso de visão computacional quando eu ainda pensava de forma mais ampla em utilizar inteligência artificial aplicada à segurança. Essa contribuição foi essencial para transformar uma ideia ainda abstrata em uma proposta concreta e definir a direção técnica que o SafetyLens seguiria.</p>
          <p>Esta nova fase do SafetyLens segue sob meu desenvolvimento, mas a história do projeto também pertence a quem ajudou a construí-lo no início.</p>
        </div>
      </section>
    </div>
  )
}
