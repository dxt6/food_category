from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from classifier.vision.dataset import prepare_dataset


class Command(BaseCommand):
    help = "将食品包装图片整理为可训练的 YOLO 数据集，并生成固定训练/验证划分。"

    def add_arguments(self, parser):
        parser.add_argument("--source", default=str(settings.VISION_DATASET_ROOT))
        parser.add_argument("--output", default=str(settings.VISION_PREPARED_DIR))
        parser.add_argument("--val-ratio", type=float, default=0.2)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--no-balance", action="store_true")

    def handle(self, *args, **options):
        try:
            manifest = prepare_dataset(
                source_root=options["source"],
                output_root=options["output"],
                val_ratio=options["val_ratio"],
                seed=options["seed"],
                force=options["force"],
                balance_train=not options["no_balance"],
            )
        except (FileNotFoundError, ValueError) as error:
            raise CommandError(str(error)) from error

        stats = manifest["stats"]
        self.stdout.write(self.style.SUCCESS(f"训练集准备完成：{manifest['data_yaml']}"))
        self.stdout.write(
            f"训练 {stats['splits']['train']} 张，验证 {stats['splits']['val']} 张，"
            f"类别均衡 {stats['balanced_samples']} 张，弱标注 {stats['weak_labels']} 张，"
            f"正常负样本 {stats['negative_samples']} 张。"
        )
