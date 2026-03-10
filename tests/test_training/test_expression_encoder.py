"""Tests for the gene expression encoder and contrastive loss."""

from __future__ import annotations

import pytest

try:
    import torch

    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False


@pytest.mark.skipif(not _TORCH_AVAILABLE, reason="PyTorch not installed")
class TestGeneExpressionEncoder:
    def test_forward_output_shape(self):
        from training.expression_encoder import GeneExpressionEncoder

        batch_size = 4
        seq_len = 50
        proj_dim = 128

        model = GeneExpressionEncoder(n_genes=1000, d_model=64, n_heads=4, n_layers=2, proj_dim=proj_dim)
        gene_ids = torch.randint(0, 1000, (batch_size, seq_len))
        values = torch.randn(batch_size, seq_len)

        out = model(gene_ids, values, modality_id=0)
        assert out.shape == (batch_size, proj_dim)

    def test_forward_different_modalities(self):
        from training.expression_encoder import GeneExpressionEncoder

        model = GeneExpressionEncoder(n_genes=500, d_model=32, n_heads=4, n_layers=1, proj_dim=64)
        gene_ids = torch.randint(0, 500, (2, 20))
        values = torch.randn(2, 20)

        out_pro = model(gene_ids, values, modality_id=0)
        out_rna = model(gene_ids, values, modality_id=1)

        # Different modality embeddings should produce different outputs
        assert not torch.allclose(out_pro, out_rna)

    def test_forward_gradient_flow(self):
        from training.expression_encoder import GeneExpressionEncoder

        model = GeneExpressionEncoder(n_genes=500, d_model=32, n_heads=4, n_layers=1, proj_dim=64)
        gene_ids = torch.randint(0, 500, (2, 10))
        values = torch.randn(2, 10)

        out = model(gene_ids, values)
        loss = out.sum()
        loss.backward()

        # Verify gradients exist
        assert model.gene_embedding.weight.grad is not None


@pytest.mark.skipif(not _TORCH_AVAILABLE, reason="PyTorch not installed")
class TestNTXentLoss:
    def test_loss_positive(self):
        from training.expression_encoder import NTXentLoss

        loss_fn = NTXentLoss(temperature=0.07)
        z1 = torch.randn(8, 64)
        z2 = torch.randn(8, 64)

        loss = loss_fn(z1, z2)
        assert loss.item() > 0

    def test_loss_identical_lower(self):
        from training.expression_encoder import NTXentLoss

        loss_fn = NTXentLoss(temperature=0.07)
        z = torch.randn(8, 64)

        # Identical pairs should have lower loss than random pairs
        loss_identical = loss_fn(z, z).item()
        loss_random = loss_fn(z, torch.randn(8, 64)).item()
        assert loss_identical < loss_random

    def test_loss_batch_size_1(self):
        from training.expression_encoder import NTXentLoss

        loss_fn = NTXentLoss()
        z1 = torch.randn(1, 32)
        z2 = torch.randn(1, 32)

        # Should not crash with batch_size=1
        loss = loss_fn(z1, z2)
        assert not torch.isnan(loss)
