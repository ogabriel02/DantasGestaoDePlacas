(() => {
  const form = document.getElementById('pedido-form');
  if (!form) return;
  const campo = nome => form.elements.namedItem(nome);
  function atualizar() {
    const modelo = campo('item_id').selectedOptions[0]?.dataset.modelo || '';
    const moto = campo('tipo_veiculo').value === 'MOTO' || /moto/i.test(modelo);
    for (const opcao of campo('posicao').options) opcao.disabled = moto && opcao.value !== 'TRASEIRA';
    if (moto) campo('posicao').value = 'TRASEIRA';
    for (const posicao of ['DIANTEIRA', 'TRASEIRA']) {
      const qr = campo('qr_' + posicao.toLowerCase());
      const ativo = campo('posicao').value === 'PAR' || campo('posicao').value === posicao;
      qr.disabled = !ativo;
      qr.required = ativo;
    }
    const colecionador = campo('cor_placa').value === 'COLECIONADOR';
    for (const opcao of campo('cor_caracteres').options) {
      opcao.disabled = ['BRANCA', 'CINZA_PRATA'].includes(opcao.value) !== colecionador;
    }
    if (campo('cor_caracteres').selectedOptions[0].disabled) campo('cor_caracteres').value = colecionador ? 'BRANCA' : 'PRETA';
  }
  for (const nome of ['tipo_veiculo', 'item_id', 'posicao', 'cor_placa']) campo(nome).addEventListener('change', atualizar);
  atualizar();
})();
