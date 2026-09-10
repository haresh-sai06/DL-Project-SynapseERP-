from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from synapse_erp.pipeline import SynapseERPPipeline
from synapse_erp.platform import StartupConversionService
from synapse_erp.preprocess import parse_ledger_line, parse_whatsapp_order
from synapse_erp.workspace import WorkspaceStore


class RealDataPipelineTests(unittest.TestCase):
    def test_empty_pipeline_does_not_inject_sample_rows(self) -> None:
        snapshot = SynapseERPPipeline().ingest()
        self.assertEqual(snapshot.source_records, [])
        self.assertEqual(snapshot.source_orders, [])
        self.assertIsNotNone(snapshot.analytics)
        self.assertEqual(snapshot.analytics.total_orders, 0)

    def test_iso_date_is_not_parsed_as_quantity(self) -> None:
        record = parse_ledger_line("2026-09-10 ramesh: chini 2 kg Rs 88")
        self.assertEqual(record.quantity, 2)
        self.assertEqual(record.amount, 88)

    def test_missing_chat_price_remains_unpriced(self) -> None:
        order = parse_whatsapp_order("kavya: 2 kg atta bhej do")
        self.assertEqual(order.quantity, 2)
        self.assertIsNone(order.amount)
        snapshot = SynapseERPPipeline().ingest(chat_lines=["kavya: 2 kg atta bhej do"])
        self.assertIsNone(snapshot.invoices[0].amount)
        self.assertEqual(snapshot.analytics.total_revenue, 0)

    def test_conversion_records_measured_nodes_and_token_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            events: list[dict] = []
            service = StartupConversionService(output_root=output_root)
            result = service.run_conversion(
                conversion_id="conv-test",
                ledger_image_paths=[],
                product_image_paths=[],
                ledger_text="2026-09-10 ramesh: chini 2 kg Rs 88",
                chat_text="kavya: 2 kg atta Rs 76",
                event_handler=events.append,
            )
            self.assertEqual(len(result.nodes), 9)
            self.assertTrue(all(node.latency_ms >= 0 for node in result.nodes))
            self.assertTrue(any(event["status"] == "completed" for event in events))
            self.assertEqual(result.snapshot["source_records"][0]["quantity"], 2)

            store = WorkspaceStore(output_root=output_root)
            token = store.create_access_token(result.conversion_id)
            store.verify_access(result.conversion_id, f"Bearer {token}")
            with self.assertRaises(PermissionError):
                store.verify_access(result.conversion_id, "Bearer wrong-token")


if __name__ == "__main__":
    unittest.main()
