"""CubiCasa floor-plan parsing network used for local inference.

Adapted from CubiCasa/CubiCasa5k at commit
c34440266665a11f4484eb06cd2e4b7d72ad76c1. The upstream work and training
artifacts are licensed CC BY-NC 4.0 and are used here only for non-commercial
evaluation/demo purposes.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class Residual(nn.Module):
    def __init__(self, num_in: int, num_out: int) -> None:
        super().__init__()
        self.numIn = num_in
        self.numOut = num_out
        self.bn = nn.BatchNorm2d(self.numIn)
        self.relu = nn.ReLU(inplace=True)
        self.conv1 = nn.Conv2d(self.numIn, self.numOut // 2, kernel_size=1, bias=True)
        self.bn1 = nn.BatchNorm2d(self.numOut // 2)
        self.conv2 = nn.Conv2d(
            self.numOut // 2,
            self.numOut // 2,
            kernel_size=3,
            stride=1,
            padding=1,
            bias=True,
        )
        self.bn2 = nn.BatchNorm2d(self.numOut // 2)
        self.conv3 = nn.Conv2d(self.numOut // 2, self.numOut, kernel_size=1, bias=True)
        if self.numIn != self.numOut:
            self.conv4 = nn.Conv2d(self.numIn, self.numOut, kernel_size=1, bias=True)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        residual = value
        output = self.bn(value)
        output = self.relu(output)
        output = self.conv1(output)
        output = self.bn1(output)
        output = self.relu(output)
        output = self.conv2(output)
        output = self.bn2(output)
        output = self.relu(output)
        output = self.conv3(output)
        if self.numIn != self.numOut:
            residual = self.conv4(value)
        return output + residual


class CubiCasaStructureModel(nn.Module):
    """Legacy CubiCasa hourglass architecture with 44 inference channels."""

    def __init__(self, n_classes: int = 44) -> None:
        super().__init__()
        self.conv1_ = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=True)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu1 = nn.ReLU(inplace=True)
        self.r01 = Residual(64, 128)
        self.maxpool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.r02 = Residual(128, 128)
        self.r03 = Residual(128, 128)
        self.r04 = Residual(128, 256)

        self.maxpool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.r11_a = Residual(256, 256)
        self.r12_a = Residual(256, 256)
        self.r13_a = Residual(256, 256)

        self.maxpool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.r21_a = Residual(256, 256)
        self.r22_a = Residual(256, 256)
        self.r23_a = Residual(256, 256)

        self.maxpool3 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.r31_a = Residual(256, 256)
        self.r32_a = Residual(256, 256)
        self.r33_a = Residual(256, 256)

        self.maxpool4 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.r41_a = Residual(256, 256)
        self.r42_a = Residual(256, 256)
        self.r43_a = Residual(256, 256)
        self.r44_a = Residual(256, 512)
        self.r45_a = Residual(512, 512)
        self.upsample4 = nn.ConvTranspose2d(512, 512, kernel_size=2, stride=2)

        self.r41_b = Residual(256, 256)
        self.r42_b = Residual(256, 256)
        self.r43_b = Residual(256, 512)

        self.r4_ = Residual(512, 512)
        self.upsample3 = nn.ConvTranspose2d(512, 512, kernel_size=2, stride=2)

        self.r31_b = Residual(256, 256)
        self.r32_b = Residual(256, 256)
        self.r33_b = Residual(256, 512)

        self.r3_ = Residual(512, 512)
        self.upsample2 = nn.ConvTranspose2d(512, 512, kernel_size=2, stride=2)

        self.r21_b = Residual(256, 256)
        self.r22_b = Residual(256, 256)
        self.r23_b = Residual(256, 512)

        self.r2_ = Residual(512, 512)
        self.upsample1 = nn.ConvTranspose2d(512, 512, kernel_size=2, stride=2)

        self.r11_b = Residual(256, 256)
        self.r12_b = Residual(256, 256)
        self.r13_b = Residual(256, 512)

        self.conv2_ = nn.Conv2d(512, 512, kernel_size=1, bias=True)
        self.bn2 = nn.BatchNorm2d(512)
        self.relu2 = nn.ReLU(inplace=True)
        self.conv3_ = nn.Conv2d(512, 256, kernel_size=1, bias=True)
        self.bn3 = nn.BatchNorm2d(256)
        self.relu3 = nn.ReLU(inplace=True)
        self.conv4_ = nn.Conv2d(256, n_classes, kernel_size=1, bias=True)
        self.upsample = nn.ConvTranspose2d(n_classes, n_classes, kernel_size=4, stride=4)

    @staticmethod
    def _upsample_add(value: torch.Tensor, lateral: torch.Tensor) -> torch.Tensor:
        if value.shape != lateral.shape:
            value = F.interpolate(
                value,
                size=lateral.shape[-2:],
                mode="bilinear",
                align_corners=False,
            )
        return value + lateral

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        output = self.conv1_(value)
        output = self.bn1(output)
        output = self.relu1(output)
        output = self.maxpool(output)
        output = self.r01(output)
        output = self.r02(output)
        output = self.r03(output)
        output = self.r04(output)

        output1a = self.maxpool1(output)
        output1a = self.r11_a(output1a)
        output1a = self.r12_a(output1a)
        output1a = self.r13_a(output1a)
        output1b = self.r11_b(output)
        output1b = self.r12_b(output1b)
        output1b = self.r13_b(output1b)

        output2a = self.maxpool2(output1a)
        output2a = self.r21_a(output2a)
        output2a = self.r22_a(output2a)
        output2a = self.r23_a(output2a)
        output2b = self.r21_b(output1a)
        output2b = self.r22_b(output2b)
        output2b = self.r23_b(output2b)

        output3a = self.maxpool3(output2a)
        output3a = self.r31_a(output3a)
        output3a = self.r32_a(output3a)
        output3a = self.r33_a(output3a)
        output3b = self.r31_b(output2a)
        output3b = self.r32_b(output3b)
        output3b = self.r33_b(output3b)

        output4a = self.maxpool4(output3a)
        output4a = self.r41_a(output4a)
        output4a = self.r42_a(output4a)
        output4a = self.r43_a(output4a)
        output4a = self.r44_a(output4a)
        output4a = self.r45_a(output4a)
        output4b = self.r41_b(output3a)
        output4b = self.r42_b(output4b)
        output4b = self.r43_b(output4b)

        output4 = self._upsample_add(self.upsample4(output4a), output4b)
        output4 = self.r4_(output4)
        output3 = self._upsample_add(self.upsample3(output4), output3b)
        output3 = self.r3_(output3)
        output2 = self._upsample_add(self.upsample2(output3), output2b)
        output2 = self.r2_(output2)
        output = self._upsample_add(self.upsample1(output2), output1b)

        output = self.conv2_(output)
        output = self.bn2(output)
        output = self.relu2(output)
        output = self.conv3_(output)
        output = self.bn3(output)
        output = self.relu3(output)
        output = self.conv4_(output)
        output = self.upsample(output)
        return torch.cat((torch.sigmoid(output[:, :21]), output[:, 21:]), dim=1)
