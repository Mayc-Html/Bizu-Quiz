
let perguntaAtual = 0;
let pontos = 0;

function mostrarPergunta(){

    const pergunta = document.getElementById("pergunta");
    const respostas = document.getElementById("respostas");

    pergunta.innerText = perguntas[perguntaAtual].pergunta;

    respostas.innerHTML = "";

    perguntas[perguntaAtual].respostas.forEach((resposta, index) => {

        const botao = document.createElement("button");

        botao.innerText = resposta;

        botao.onclick = () => verificarResposta(index);

        respostas.appendChild(botao);
    });
}

function verificarResposta(index){

    if(index === perguntas[perguntaAtual].correta){
        pontos++;
    }

    perguntaAtual++;

    if(perguntaAtual < perguntas.length){
        mostrarPergunta();
    }else{
        mostrarResultado();
    }
}

function mostrarResultado(){

    document.querySelector(".quiz").innerHTML = `
        <h2>Quiz Finalizado!</h2>
        <p>Você acertou ${pontos} de ${perguntas.length} perguntas.</p>

        <button onclick="location.reload()">
            Reiniciar
        </button>
    `;
}

mostrarPergunta();
