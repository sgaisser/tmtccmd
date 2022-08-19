import argparse
from unittest import TestCase

from tmtccmd.config.args import (
    add_default_mode_arguments,
    add_default_procedure_arguments_without_subparser,
    add_generic_arguments,
    add_default_com_if_arguments,
)


class TestArgsParsing(TestCase):
    def setUp(self) -> None:
        self.arg_parser = argparse.ArgumentParser()

    def test_basic_arg_parser_mode_empty(self):
        add_default_mode_arguments(self.arg_parser)
        args = self.arg_parser.parse_args([])
        self.assertEqual(args.mode, None)

    def test_valid_argument_0(self):
        add_default_mode_arguments(self.arg_parser)
        args = self.arg_parser.parse_args(["-m", "one-q"])
        self.assertEqual(args.mode, "one-q")

    def test_valid_argument_1(self):
        add_default_mode_arguments(self.arg_parser)
        args = self.arg_parser.parse_args(["--mode", "one-q"])
        self.assertEqual(args.mode, "one-q")

    def test_def_proc_argument_empty(self):
        add_default_procedure_arguments_without_subparser(self.arg_parser)
        args = self.arg_parser.parse_args([])
        self.assertIsNone(args.service)
        self.assertIsNone(args.op_code)

    def test_def_proc_argument_valid(self):
        add_default_procedure_arguments_without_subparser(self.arg_parser)
        args = self.arg_parser.parse_args(["-s", "17", "-o", "ping"])
        self.assertEqual(args.service, "17")
        self.assertEqual(args.op_code, "ping")

    def test_generic_arguments_empty(self):
        add_generic_arguments(self.arg_parser)
        args = self.arg_parser.parse_args([])
        self.assertIsNone(args.delay)
        self.assertFalse(args.listener)
        self.assertFalse(args.gui)

    def test_generic_arguments_valid(self):
        add_generic_arguments(self.arg_parser)
        args = self.arg_parser.parse_args(["-d", "2.0", "-l", "-g"])
        self.assertEqual(args.delay, 2.0)
        self.assertTrue(args.listener, True)
        self.assertEqual(args.gui, True)

    def test_com_if_arguments_empty(self):
        add_default_com_if_arguments(self.arg_parser)
        args = self.arg_parser.parse_args([])
        self.assertEqual(args.com_if, "unspec")

    def test_com_if_arguments_valid(self):
        add_default_com_if_arguments(self.arg_parser)
        args = self.arg_parser.parse_args(["-c", "udp"])
        self.assertEqual(args.com_if, "udp")
