import torch 
import numpy as np
from torch import Tensor
from torch.utils.data import Dataset, DataLoader
from torchvision import io
from pathlib import Path
from typing import Tuple



class MHPv1(Dataset):
    """
    4980 images each with at least 2 persons (average 3)
    3000 images for training 
    1000 images for validation
    980 images for testing
    num_classes: 18+background
    """
    CLASSES = ['background', 'hat', 'hair', 'sunglass', 'upper-clothes', 'skirt', 'pants', 'dress', 'belt', 'left-shoe', 'right-shoe', 'face', 'left-leg', 'right-leg', 'left-arm', 'right-arm', 'bag', 'sacrf', 'torso-skin']
    PALETTE = torch.tensor([[0, 0, 0], [128, 0, 0], [254, 0, 0], [0, 85, 0], [169, 0, 51], [254, 85, 0], [255, 0, 85], [0, 119, 220], [85, 85, 0], [190, 153, 153], [85, 51, 0], [52, 86, 128], [0, 128, 0], [0, 0, 254], [51, 169, 220], [0, 254, 254], [85, 254, 169], [169, 254, 85], [254, 254, 0]])

    def __init__(self, root: str, split: str = 'train', transform = None) -> None:
        super().__init__()
        assert split in ['train', 'val', 'test']
        self.transform = transform
        self.n_classes = len(self.CLASSES)
        self.ignore_label = 255

        self.images, self.labels = self.get_files(root, split)
        print(f"Found {len(self.images)} {split} images.")

    def get_files(self, root: str, split: str):
        root = Path(root)
        all_labels = list((root / 'annotations').rglob('*.png'))
        images, labels = [], []

        flist = 'test_list.txt' if split == 'test' else 'train_list.txt'
        with open(root / flist) as f:
            all_files = f.read().splitlines()
        
        if split == 'train':
            files = all_files[:3000]
        elif split == 'val':
            files = all_files[3000:]
        else:
            files = all_files
        
        for f in files:
            images.append(root / 'images' / f)
            img_name = f.split('.')[0]
            labels_per_images = list(filter(lambda x: x.stem.startswith(img_name), all_labels))
            assert labels_per_images != []
            labels.append(labels_per_images)

        assert len(images) == len(labels)
        return images, labels

    def __len__(self) -> int:
        return len(self.images)
    
    def __getitem__(self, index: int) -> Tuple[Tensor, Tensor]:
        img_path = str(self.images[index])
        lbl_paths = self.labels[index]

        image = io.read_image(img_path)
        label = self.read_label(lbl_paths)

        if self.transform:
            image, label = self.transform(image, label)
        return image, label.squeeze().long()

    def read_label(self, lbl_paths: list) -> Tensor:
        labels = None
        label_idx = None

        for lbl_path in lbl_paths:
            label = io.read_image(str(lbl_path)).squeeze().numpy()

            if label_idx is None:
                label_idx = np.zeros(label.shape, dtype=np.uint8)
            label = np.ma.masked_array(label, mask=label_idx)
            label_idx += np.minimum(label, 1)
            if labels is None:
                labels = label
            else:
                labels += label
    
        return torch.from_numpy(labels.data).unsqueeze(0).to(torch.uint8)

    def decode(self, label: Tensor) -> Tensor:
        return self.PALETTE[label.to(int)]


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from torchvision import transforms as T
    from torchvision.utils import make_grid
    from augmentations import Compose, Resize, Normalize

    root = 'C:\\Users\\sithu\\Documents\\Datasets\\LV-MHP-v1'
    transform = Compose([Resize((480, 640)), Normalize()])

    dataset = MHPv1(root, split="train", transform=transform)
    dataloader = DataLoader(dataset, shuffle=True, batch_size=4)
    image, label = next(iter(dataloader))
    print(image.shape, label.shape)
    print(label.unique())
    labels = [dataset.decode(lbl).permute(2, 0, 1) for lbl in label]
    labels = torch.stack(labels)

    inv_normalize = T.Normalize(
        mean=(-0.485/0.229, -0.456/0.224, -0.406/0.225),
        std=(1/0.229, 1/0.224, 1/0.225)
    )
    image = inv_normalize(image)
    image *= 255
    images = torch.vstack([image, labels])
    
    plt.imshow(make_grid(images, nrow=4).to(torch.uint8).numpy().transpose((1, 2, 0)))
    plt.show()
