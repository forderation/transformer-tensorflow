import click
import time

from baselines import logger
from data import *
from transformer import *


@click.command()
@click.option('--seq-len', type=int, default=20, show_default=True, help="Input sequence length.")
@click.option('--d-model', type=int, default=512, show_default=True, help="d_model")
@click.option('--n-head', type=int, default=8, show_default=True, help="n_head")
@click.option('--batch-size', type=int, default=32, show_default=True, help="Batch size")
@click.option('--max-steps', type=int, default=100000, show_default=True, help="Max train steps.")
@click.option('--dataset', type=click.Choice(['iwslt15', 'wmt14', 'wmt15']),
              default='iwslt15', show_default=True, help="Which translation dataset to use.")
def train(seq_len=20, d_model=512, n_head=8, batch_size=64, max_steps=100000, dataset='iwslt15'):
    m = DatasetManager(dataset)
    m.maybe_download_data_files()
    m.load_vocab()

    train_params = dict(
        learning_rate=1e-4,
        batch_size=batch_size,
        seq_len=seq_len,
        max_steps=max_steps,
    )

    tf_sess_config = dict(
        allow_soft_placement=True,
        intra_op_parallelism_threads=8,
        inter_op_parallelism_threads=4,
    )

    model_name = f'transformer-seq{seq_len}-d{d_model}-head{n_head}-{int(time.time())}'
    transformer = Transformer(
        num_heads=n_head,
        d_model=d_model,
        model_name=model_name,
        tf_sess_config=tf_sess_config
    )
    transformer.build_model(m.source_id2word, m.target_id2word, PAD_ID, **train_params)
    transformer.print_trainable_variables()

    train_data_iter = m.data_generator(batch_size, seq_len + 1, data_type='train')
    test_data_iter = m.data_generator(batch_size, seq_len + 1, data_type='test')
    logger.configure(dir=transformer.log_dir, format_strs=['stdout', 'csv'])

    transformer.init()  # step = 0
    while transformer.step < max_steps:
        input_ids, target_ids = next(train_data_iter)
        meta = transformer.train(input_ids, target_ids)
        for k, v in meta.items():
            logger.logkv(k, v)

        if transformer.step % 100 == 0:
            test_inp_ids, test_target_ids = next(test_data_iter)
            meta = transformer.evaluate(test_inp_ids, test_target_ids)
            for k, v in meta.items():
                logger.logkv('test_' + k, v)
            logger.dumpkvs()

    transformer.done()


if __name__ == '__main__':
    train()
