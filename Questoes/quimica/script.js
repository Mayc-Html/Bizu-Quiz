let perguntas = [];
let perguntaAtual = 0;

fetch("perguntas.json")
  .then(resposta => resposta.json())
  .then(dados => {

    perguntas = dados.perguntas;

    carregarPergunta();

  });

function carregarPergunta() {

  document.getElementById("pergunta").innerText =
    perguntas[perguntaAtual].pergunta;

  document.getElementById("bt1").innerText =
    perguntas[perguntaAtual].respostas[0];

  document.getElementById("bt2").innerText =
    perguntas[perguntaAtual].respostas[1];

  document.getElementById("bt3").innerText =
    perguntas[perguntaAtual].respostas[2];

  document.getElementById("bt4").innerText =
    perguntas[perguntaAtual].respostas[3];

  document.querySelector(".numero").innerText =
    (perguntaAtual + 1) + ".";
}

function responder(opcao) {

  if (opcao === perguntas[perguntaAtual].correta) {

    perguntaAtual++;

    if (perguntaAtual < perguntas.length) {

      carregarPergunta();

    } else {

      window.location.href = "parabens.html";

    }

  } else {

    window.location.href = "erro.html";

  }
}