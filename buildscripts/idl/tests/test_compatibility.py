#!/usr/bin/env python3
#
# Copyright (C) 2021-present MongoDB, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the Server Side Public License, version 1,
# as published by MongoDB, Inc.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Server Side Public License for more details.
#
# You should have received a copy of the Server Side Public License
# along with this program. If not, see
# <http://www.mongodb.com/licensing/server-side-public-license>.
#
# As a special exception, the copyright holders give permission to link the
# code of portions of this program with the OpenSSL library under certain
# conditions as described in each individual source file and distribute
# linked combinations including the program with the OpenSSL library. You
# must comply with the Server Side Public License in all respects for
# all of the code used other than as permitted herein. If you modify file(s)
# with this exception, you may extend this exception to your version of the
# file(s), but you are not obligated to do so. If you do not wish to do so,
# delete this exception statement from your version. If you delete this
# exception statement from all source files in the program, then also delete
# it in the license file.
#
"""Test cases for IDL compatibility checker."""

import unittest
import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

#pylint: disable=wrong-import-position
import idl_check_compatibility
import idl_compatibility_errors

#pylint: enable=wrong-import-position


class TestIDLCompatibilityChecker(unittest.TestCase):
    """Test the IDL Compatibility Checker."""

    def test_should_pass(self):
        """Tests that compatible old and new IDL commands should pass."""
        dir_path = path.dirname(path.realpath(__file__))
        self.assertFalse(
            idl_check_compatibility.check_compatibility(
                path.join(dir_path, "compatibility_test_pass/old"),
                path.join(dir_path, "compatibility_test_pass/new"), ["src"]).has_errors())

    def test_should_abort(self):
        """Tests that invalid old and new IDL commands should cause script to abort."""
        dir_path = path.dirname(path.realpath(__file__))
        # Test that when old command has a reply field with an invalid reply type, the script aborts.
        with self.assertRaises(SystemExit):
            idl_check_compatibility.check_compatibility(
                path.join(dir_path, "compatibility_test_fail/abort/invalid_reply_field_type"),
                path.join(dir_path, "compatibility_test_fail/abort/valid_reply_field_type"),
                ["src"])

        # Test that when new command has a reply field with an invalid reply type, the script aborts.
        with self.assertRaises(SystemExit):
            idl_check_compatibility.check_compatibility(
                path.join(dir_path, "compatibility_test_fail/abort/valid_reply_field_type"),
                path.join(dir_path, "compatibility_test_fail/abort/invalid_reply_field_type"),
                ["src"])

        # Test that when new command has a parameter with an invalid type, the script aborts.
        with self.assertRaises(SystemExit):
            idl_check_compatibility.check_compatibility(
                path.join(dir_path, "compatibility_test_fail/abort/invalid_command_parameter_type"),
                path.join(dir_path, "compatibility_test_fail/abort/valid_command_parameter_type"),
                ["src"])

        # Test that when new command has a parameter with an invalid type, the script aborts.
        with self.assertRaises(SystemExit):
            idl_check_compatibility.check_compatibility(
                path.join(dir_path, "compatibility_test_fail/abort/valid_command_parameter_type"),
                path.join(dir_path, "compatibility_test_fail/abort/invalid_command_parameter_type"),
                ["src"])

    # pylint: disable=too-many-locals,too-many-statements
    def test_should_fail(self):
        """Tests that incompatible old and new IDL commands should fail."""
        dir_path = path.dirname(path.realpath(__file__))
        error_collection = idl_check_compatibility.check_compatibility(
            path.join(dir_path, "compatibility_test_fail/old"),
            path.join(dir_path, "compatibility_test_fail/new"), ["src"])

        self.assertTrue(error_collection.has_errors())
        self.assertTrue(error_collection.count() == 97)

        invalid_api_version_new_error = error_collection.get_error_by_command_name(
            "invalidAPIVersionNew")
        self.assertTrue(invalid_api_version_new_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_INVALID_API_VERSION)
        self.assertRegex(str(invalid_api_version_new_error), "invalidAPIVersionNew")

        duplicate_command_new_error = error_collection.get_error_by_command_name(
            "duplicateCommandNew")
        self.assertTrue(duplicate_command_new_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_DUPLICATE_COMMAND_NAME)
        self.assertRegex(str(duplicate_command_new_error), "duplicateCommandNew")

        invalid_api_version_old_error = error_collection.get_error_by_command_name(
            "invalidAPIVersionOld")
        self.assertTrue(invalid_api_version_old_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_INVALID_API_VERSION)
        self.assertRegex(str(invalid_api_version_old_error), "invalidAPIVersionOld")

        duplicate_command_old_error = error_collection.get_error_by_command_name(
            "duplicateCommandOld")
        self.assertTrue(duplicate_command_old_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_DUPLICATE_COMMAND_NAME)
        self.assertRegex(str(duplicate_command_old_error), "duplicateCommandOld")

        removed_command_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_REMOVED_COMMAND)
        self.assertRegex(str(removed_command_error), "removedCommand")

        removed_command_parameter_error = error_collection.get_error_by_command_name(
            "removedCommandParameter")
        self.assertTrue(removed_command_parameter_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_REMOVED_COMMAND_PARAMETER)
        self.assertRegex(str(removed_command_parameter_error), "removedCommandParameter")

        added_required_command_parameter_error = error_collection.get_error_by_command_name(
            "addedNewCommandParameterRequired")
        self.assertTrue(added_required_command_parameter_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_ADDED_REQUIRED_COMMAND_PARAMETER)
        self.assertRegex(
            str(added_required_command_parameter_error), "addedNewCommandParameterRequired")

        command_parameter_unstable_error = error_collection.get_error_by_command_name(
            "commandParameterUnstable")
        self.assertTrue(command_parameter_unstable_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_UNSTABLE)
        self.assertRegex(str(command_parameter_unstable_error), "commandParameterUnstable")

        command_parameter_stable_required_error = error_collection.get_error_by_command_name(
            "commandParameterStableRequired")
        self.assertTrue(command_parameter_stable_required_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_STABLE_REQUIRED)
        self.assertRegex(
            str(command_parameter_stable_required_error), "commandParameterStableRequired")

        command_parameter_required_error = error_collection.get_error_by_command_name(
            "commandParameterRequired")
        self.assertTrue(command_parameter_required_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_REQUIRED)
        self.assertRegex(str(command_parameter_required_error), "commandParameterRequired")

        old_command_parameter_type_bson_any_error = error_collection.get_error_by_command_name(
            "oldCommandParameterTypeBsonSerializationAny")
        self.assertTrue(
            old_command_parameter_type_bson_any_error.error_id == idl_compatibility_errors.
            ERROR_ID_OLD_COMMAND_PARAMETER_TYPE_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(
            str(old_command_parameter_type_bson_any_error),
            "oldCommandParameterTypeBsonSerializationAny")

        new_command_parameter_type_bson_any_error = error_collection.get_error_by_command_name(
            "newCommandParameterTypeBsonSerializationAny")
        self.assertTrue(
            new_command_parameter_type_bson_any_error.error_id == idl_compatibility_errors.
            ERROR_ID_NEW_COMMAND_PARAMETER_TYPE_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(
            str(new_command_parameter_type_bson_any_error),
            "newCommandParameterTypeBsonSerializationAny")

        old_param_type_bson_any_allow_list_error = error_collection.get_error_by_command_name(
            "oldParamTypeBsonAnyAllowList")
        self.assertTrue(
            old_param_type_bson_any_allow_list_error.error_id == idl_compatibility_errors.
            ERROR_ID_OLD_COMMAND_PARAMETER_TYPE_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(
            str(old_param_type_bson_any_allow_list_error), "oldParamTypeBsonAnyAllowList")

        new_param_type_bson_any_allow_list_error = error_collection.get_error_by_command_name(
            "newParamTypeBsonAnyAllowList")
        self.assertTrue(
            new_param_type_bson_any_allow_list_error.error_id == idl_compatibility_errors.
            ERROR_ID_NEW_COMMAND_PARAMETER_TYPE_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(
            str(new_param_type_bson_any_allow_list_error), "newParamTypeBsonAnyAllowList")

        command_parameter_type_bson_any_not_allowed_error = error_collection.get_error_by_command_name(
            "commandParameterTypeBsonSerializationAnyNotAllowed")
        self.assertTrue(
            command_parameter_type_bson_any_not_allowed_error.error_id == idl_compatibility_errors.
            ERROR_ID_COMMAND_PARAMETER_BSON_SERIALIZATION_TYPE_ANY_NOT_ALLOWED)
        self.assertRegex(
            str(command_parameter_type_bson_any_not_allowed_error),
            "commandParameterTypeBsonSerializationAnyNotAllowed")

        command_parameter_cpp_type_not_equal_error = error_collection.get_error_by_command_name(
            "commandParameterCppTypeNotEqual")
        self.assertTrue(command_parameter_cpp_type_not_equal_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_CPP_TYPE_NOT_EQUAL)
        self.assertRegex(
            str(command_parameter_cpp_type_not_equal_error), "commandParameterCppTypeNotEqual")

        new_command_parameter_type_enum_not_superset = error_collection.get_error_by_command_name(
            "newCommandParameterTypeEnumNotSuperset")
        self.assertTrue(new_command_parameter_type_enum_not_superset.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_TYPE_NOT_SUPERSET)
        self.assertRegex(
            str(new_command_parameter_type_enum_not_superset),
            "newCommandParameterTypeEnumNotSuperset")

        new_command_parameter_type_not_enum = error_collection.get_error_by_command_name(
            "newCommandParameterTypeNotEnum")
        self.assertTrue(new_command_parameter_type_not_enum.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_COMMAND_PARAMETER_TYPE_NOT_ENUM)
        self.assertRegex(str(new_command_parameter_type_not_enum), "newCommandParameterTypeNotEnum")

        new_command_parameter_type_not_struct = error_collection.get_error_by_command_name(
            "newCommandParameterTypeNotStruct")
        self.assertTrue(new_command_parameter_type_not_struct.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_COMMAND_PARAMETER_TYPE_NOT_STRUCT)
        self.assertRegex(
            str(new_command_parameter_type_not_struct), "newCommandParameterTypeNotStruct")

        new_command_parameter_type_enum_or_struct_one = error_collection.get_error_by_command_name(
            "newCommandParameterTypeEnumOrStructOne")
        self.assertTrue(new_command_parameter_type_enum_or_struct_one.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_COMMAND_PARAMETER_TYPE_ENUM_OR_STRUCT)
        self.assertRegex(
            str(new_command_parameter_type_enum_or_struct_one),
            "newCommandParameterTypeEnumOrStructOne")

        new_command_parameter_type_enum_or_struct_two = error_collection.get_error_by_command_name(
            "newCommandParameterTypeEnumOrStructTwo")
        self.assertTrue(new_command_parameter_type_enum_or_struct_two.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_COMMAND_PARAMETER_TYPE_ENUM_OR_STRUCT)
        self.assertRegex(
            str(new_command_parameter_type_enum_or_struct_two),
            "newCommandParameterTypeEnumOrStructTwo")

        new_command_parameter_type_bson_not_superset = error_collection.get_error_by_command_name(
            "newCommandParameterTypeBsonNotSuperset")
        self.assertTrue(new_command_parameter_type_bson_not_superset.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_TYPE_NOT_SUPERSET)
        self.assertRegex(
            str(new_command_parameter_type_bson_not_superset),
            "newCommandParameterTypeBsonNotSuperset")

        new_command_parameter_type_recursive_one_error = error_collection.get_error_by_command_name(
            "newCommandParameterTypeStructRecursiveOne")
        self.assertTrue(new_command_parameter_type_recursive_one_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_UNSTABLE)
        self.assertRegex(
            str(new_command_parameter_type_recursive_one_error),
            "newCommandParameterTypeStructRecursiveOne")

        new_command_parameter_type_recursive_two_error = error_collection.get_error_by_command_name(
            "newCommandParameterTypeStructRecursiveTwo")
        self.assertTrue(new_command_parameter_type_recursive_two_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_TYPE_NOT_SUPERSET)
        self.assertRegex(
            str(new_command_parameter_type_recursive_two_error),
            "newCommandParameterTypeStructRecursiveTwo")

        new_reply_field_unstable_error = error_collection.get_error_by_command_name(
            "newReplyFieldUnstable")
        self.assertTrue(new_reply_field_unstable_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_UNSTABLE)
        self.assertRegex(str(new_reply_field_unstable_error), "newReplyFieldUnstable")

        new_reply_field_optional_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_OPTIONAL)
        self.assertRegex(str(new_reply_field_optional_error), "newReplyFieldOptional")

        new_reply_field_missing_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_MISSING)
        self.assertRegex(str(new_reply_field_missing_error), "newReplyFieldMissing")

        imported_reply_field_unstable_error = error_collection.get_error_by_command_name(
            "importedReplyCommand")
        self.assertTrue(imported_reply_field_unstable_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_UNSTABLE)
        self.assertRegex(str(imported_reply_field_unstable_error), "importedReplyCommand")

        new_reply_field_type_enum_not_subset_error = error_collection.get_error_by_command_name(
            "newReplyFieldTypeEnumNotSubset")
        self.assertTrue(new_reply_field_type_enum_not_subset_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_REPLY_FIELD_NOT_SUBSET)
        self.assertRegex(
            str(new_reply_field_type_enum_not_subset_error), "newReplyFieldTypeEnumNotSubset")

        new_reply_field_type_not_enum_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_TYPE_NOT_ENUM)
        self.assertRegex(str(new_reply_field_type_not_enum_error), "newReplyFieldTypeNotEnum")

        new_reply_field_type_not_struct_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_TYPE_NOT_STRUCT)
        self.assertRegex(str(new_reply_field_type_not_struct_error), "newReplyFieldTypeNotStruct")

        new_reply_field_type_enum_or_struct_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_TYPE_ENUM_OR_STRUCT)
        self.assertRegex(
            str(new_reply_field_type_enum_or_struct_error), "newReplyFieldTypeEnumOrStruct")

        new_reply_field_type_bson_not_subset_error = error_collection.get_error_by_command_name(
            "newReplyFieldTypeBsonNotSubset")
        self.assertTrue(new_reply_field_type_bson_not_subset_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_REPLY_FIELD_NOT_SUBSET)
        self.assertRegex(
            str(new_reply_field_type_bson_not_subset_error), "newReplyFieldTypeBsonNotSubset")

        new_reply_field_type_bson_not_subset_two_error = error_collection.get_error_by_command_name(
            "newReplyFieldTypeBsonNotSubsetTwo")
        self.assertTrue(new_reply_field_type_bson_not_subset_two_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_REPLY_FIELD_NOT_SUBSET)
        self.assertRegex(
            str(new_reply_field_type_bson_not_subset_two_error),
            "newReplyFieldTypeBsonNotSubsetTwo")

        old_reply_field_type_bson_any_error = error_collection.get_error_by_command_name(
            "oldReplyFieldTypeBsonAny")
        self.assertTrue(old_reply_field_type_bson_any_error.error_id == idl_compatibility_errors.
                        ERROR_ID_OLD_REPLY_FIELD_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(str(old_reply_field_type_bson_any_error), "oldReplyFieldTypeBsonAny")

        new_reply_field_type_bson_any_error = error_collection.get_error_by_command_name(
            "newReplyFieldTypeBsonAny")
        self.assertTrue(new_reply_field_type_bson_any_error.error_id == idl_compatibility_errors.
                        ERROR_ID_NEW_REPLY_FIELD_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(str(new_reply_field_type_bson_any_error), "newReplyFieldTypeBsonAny")

        old_reply_field_type_bson_any_allow_list_error = error_collection.get_error_by_command_name(
            "oldReplyFieldTypeBsonAnyAllowList")
        self.assertTrue(
            old_reply_field_type_bson_any_allow_list_error.error_id ==
            idl_compatibility_errors.ERROR_ID_OLD_REPLY_FIELD_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(
            str(old_reply_field_type_bson_any_allow_list_error),
            "oldReplyFieldTypeBsonAnyAllowList")

        new_reply_field_type_bson_any_allow_list_error = error_collection.get_error_by_command_name(
            "newReplyFieldTypeBsonAnyAllowList")
        self.assertTrue(
            new_reply_field_type_bson_any_allow_list_error.error_id ==
            idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(
            str(new_reply_field_type_bson_any_allow_list_error),
            "newReplyFieldTypeBsonAnyAllowList")

        reply_field_type_bson_any_not_allowed_error = error_collection.get_error_by_command_name(
            "replyFieldTypeBsonAnyNotAllowed")
        self.assertTrue(
            reply_field_type_bson_any_not_allowed_error.error_id ==
            idl_compatibility_errors.ERROR_ID_REPLY_FIELD_BSON_SERIALIZATION_TYPE_ANY_NOT_ALLOWED)
        self.assertRegex(
            str(reply_field_type_bson_any_not_allowed_error), "replyFieldTypeBsonAnyNotAllowed")

        reply_field_type_bson_any_with_variant_error = error_collection.get_error_by_command_name_and_error_id(
            "replyFieldTypeBsonAnyWithVariant",
            idl_compatibility_errors.ERROR_ID_OLD_REPLY_FIELD_BSON_SERIALIZATION_TYPE_ANY)
        self.assertTrue(
            reply_field_type_bson_any_with_variant_error.error_id ==
            idl_compatibility_errors.ERROR_ID_OLD_REPLY_FIELD_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(
            str(reply_field_type_bson_any_with_variant_error), "replyFieldTypeBsonAnyWithVariant")

        reply_field_type_bson_any_with_variant_error = error_collection.get_error_by_command_name_and_error_id(
            "replyFieldTypeBsonAnyWithVariant",
            idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_BSON_SERIALIZATION_TYPE_ANY)
        self.assertTrue(
            reply_field_type_bson_any_with_variant_error.error_id ==
            idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(
            str(reply_field_type_bson_any_with_variant_error), "replyFieldTypeBsonAnyWithVariant")

        reply_field_cpp_type_not_equal_error = error_collection.get_error_by_command_name(
            "replyFieldCppTypeNotEqual")
        self.assertTrue(reply_field_cpp_type_not_equal_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_REPLY_FIELD_CPP_TYPE_NOT_EQUAL)
        self.assertRegex(str(reply_field_cpp_type_not_equal_error), "replyFieldCppTypeNotEqual")

        new_reply_field_type_struct_one_error = error_collection.get_error_by_command_name(
            "newReplyFieldTypeStructRecursiveOne")
        self.assertTrue(new_reply_field_type_struct_one_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_UNSTABLE)
        self.assertRegex(
            str(new_reply_field_type_struct_one_error), "newReplyFieldTypeStructRecursiveOne")

        new_reply_field_type_struct_two_error = error_collection.get_error_by_command_name(
            "newReplyFieldTypeStructRecursiveTwo")
        self.assertTrue(new_reply_field_type_struct_two_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_REPLY_FIELD_NOT_SUBSET)
        self.assertRegex(
            str(new_reply_field_type_struct_two_error), "newReplyFieldTypeStructRecursiveTwo")

        new_namespace_not_ignored_error = error_collection.get_error_by_command_name(
            "newNamespaceNotIgnored")
        self.assertTrue(new_namespace_not_ignored_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_NAMESPACE_INCOMPATIBLE)
        self.assertRegex(str(new_namespace_not_ignored_error), "newNamespaceNotIgnored")

        new_namespace_not_concatenate_with_db_or_uuid_error = error_collection.get_error_by_command_name(
            "newNamespaceNotConcatenateWithDbOrUuid")
        self.assertTrue(new_namespace_not_concatenate_with_db_or_uuid_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_NAMESPACE_INCOMPATIBLE)
        self.assertRegex(
            str(new_namespace_not_concatenate_with_db_or_uuid_error),
            "newNamespaceNotConcatenateWithDbOrUuid")

        new_namespace_not_concatenate_with_db_error = error_collection.get_error_by_command_name(
            "newNamespaceNotConcatenateWithDb")
        self.assertTrue(new_namespace_not_concatenate_with_db_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_NAMESPACE_INCOMPATIBLE)
        self.assertRegex(
            str(new_namespace_not_concatenate_with_db_error), "newNamespaceNotConcatenateWithDb")

        new_namespace_not_type_error = error_collection.get_error_by_command_name(
            "newNamespaceNotType")
        self.assertTrue(new_namespace_not_type_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_NAMESPACE_INCOMPATIBLE)
        self.assertRegex(str(new_namespace_not_type_error), "newNamespaceNotType")

        old_type_bson_any_error = error_collection.get_error_by_command_name("oldTypeBsonAny")
        self.assertTrue(old_type_bson_any_error.error_id == idl_compatibility_errors.
                        ERROR_ID_OLD_COMMAND_TYPE_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(str(old_type_bson_any_error), "oldTypeBsonAny")

        new_type_bson_any_error = error_collection.get_error_by_command_name("newTypeBsonAny")
        self.assertTrue(new_type_bson_any_error.error_id == idl_compatibility_errors.
                        ERROR_ID_NEW_COMMAND_TYPE_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(str(new_type_bson_any_error), "newTypeBsonAny")

        old_type_bson_any_allow_list_error = error_collection.get_error_by_command_name(
            "oldTypeBsonAnyAllowList")
        self.assertTrue(old_type_bson_any_allow_list_error.error_id == idl_compatibility_errors.
                        ERROR_ID_OLD_COMMAND_TYPE_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(str(old_type_bson_any_allow_list_error), "oldTypeBsonAnyAllowList")

        new_type_bson_any_allow_list_error = error_collection.get_error_by_command_name(
            "newTypeBsonAnyAllowList")
        self.assertTrue(new_type_bson_any_allow_list_error.error_id == idl_compatibility_errors.
                        ERROR_ID_NEW_COMMAND_TYPE_BSON_SERIALIZATION_TYPE_ANY)
        self.assertRegex(str(new_type_bson_any_allow_list_error), "newTypeBsonAnyAllowList")

        type_bson_any_not_allowed_error = error_collection.get_error_by_command_name(
            "typeBsonAnyNotAllowed")
        self.assertTrue(type_bson_any_not_allowed_error.error_id == idl_compatibility_errors.
                        ERROR_ID_COMMAND_TYPE_BSON_SERIALIZATION_TYPE_ANY_NOT_ALLOWED)
        self.assertRegex(str(type_bson_any_not_allowed_error), "typeBsonAnyNotAllowed")

        command_cpp_type_not_equal_error = error_collection.get_error_by_command_name(
            "commandCppTypeNotEqual")
        self.assertTrue(command_cpp_type_not_equal_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_CPP_TYPE_NOT_EQUAL)
        self.assertRegex(str(command_cpp_type_not_equal_error), "commandCppTypeNotEqual")

        new_type_not_enum_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_COMMAND_TYPE_NOT_ENUM)
        self.assertRegex(str(new_type_not_enum_error), "newTypeNotEnum")

        new_type_not_struct_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_COMMAND_TYPE_NOT_STRUCT)
        self.assertRegex(str(new_type_not_struct_error), "newTypeNotStruct")

        new_type_enum_or_struct_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_COMMAND_TYPE_ENUM_OR_STRUCT)
        self.assertRegex(str(new_type_enum_or_struct_error), "newTypeEnumOrStruct")

        new_type_not_superset_error = error_collection.get_error_by_command_name(
            "newTypeNotSuperset")
        self.assertTrue(new_type_not_superset_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_TYPE_NOT_SUPERSET)
        self.assertRegex(str(new_type_not_superset_error), "newTypeNotSuperset")

        new_type_enum_not_superset_error = error_collection.get_error_by_command_name(
            "newTypeEnumNotSuperset")
        self.assertTrue(new_type_enum_not_superset_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_TYPE_NOT_SUPERSET)
        self.assertRegex(str(new_type_enum_not_superset_error), "newTypeEnumNotSuperset")

        new_type_struct_recursive_error = error_collection.get_error_by_command_name(
            "newTypeStructRecursive")
        self.assertTrue(new_type_struct_recursive_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_COMMAND_TYPE_FIELD_UNSTABLE)
        self.assertRegex(str(new_type_struct_recursive_error), "newTypeStructRecursive")

        new_type_field_unstable_error = error_collection.get_error_by_command_name(
            "newTypeFieldUnstable")
        self.assertTrue(new_type_field_unstable_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_COMMAND_TYPE_FIELD_UNSTABLE)
        self.assertRegex(str(new_type_field_unstable_error), "newTypeFieldUnstable")

        new_type_field_required_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_COMMAND_TYPE_FIELD_REQUIRED)
        self.assertRegex(str(new_type_field_required_error), "newTypeFieldRequired")

        new_type_field_missing_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_COMMAND_TYPE_FIELD_MISSING)
        self.assertRegex(str(new_type_field_missing_error), "newTypeFieldMissing")

        new_type_field_added_required_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_COMMAND_TYPE_FIELD_ADDED_REQUIRED)
        self.assertRegex(str(new_type_field_added_required_error), "newTypeFieldAddedRequired")

        new_type_field_stable_required_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_COMMAND_TYPE_FIELD_STABLE_REQUIRED)
        self.assertRegex(str(new_type_field_stable_required_error), "newTypeFieldStableRequired")

        new_reply_field_variant_type_error = error_collection.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_VARIANT_TYPE)
        self.assertRegex(str(new_reply_field_variant_type_error), "newReplyFieldVariantType")

        new_reply_field_variant_not_subset_error = error_collection.get_error_by_command_name(
            "newReplyFieldVariantNotSubset")
        self.assertTrue(new_reply_field_variant_not_subset_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_VARIANT_TYPE_NOT_SUBSET)
        self.assertRegex(
            str(new_reply_field_variant_not_subset_error), "newReplyFieldVariantNotSubset")

        new_reply_field_variant_not_subset_two_errors = error_collection.get_all_errors_by_command_name(
            "newReplyFieldVariantNotSubsetTwo")
        self.assertTrue(len(new_reply_field_variant_not_subset_two_errors) == 2)
        for error in new_reply_field_variant_not_subset_two_errors:
            self.assertTrue(error.error_id == idl_compatibility_errors.
                            ERROR_ID_NEW_REPLY_FIELD_VARIANT_TYPE_NOT_SUBSET)

        new_reply_field_variant_recursive_error = error_collection.get_error_by_command_name(
            "replyFieldVariantRecursive")
        self.assertTrue(new_reply_field_variant_recursive_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_REPLY_FIELD_NOT_SUBSET)
        self.assertRegex(str(new_reply_field_variant_recursive_error), "replyFieldVariantRecursive")

        new_reply_field_variant_struct_not_subset_error = error_collection.get_error_by_command_name(
            "newReplyFieldVariantStructNotSubset")
        self.assertTrue(new_reply_field_variant_struct_not_subset_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_VARIANT_TYPE_NOT_SUBSET)
        self.assertRegex(
            str(new_reply_field_variant_struct_not_subset_error),
            "newReplyFieldVariantStructNotSubset")

        new_reply_field_variant_struct_recursive_error = error_collection.get_error_by_command_name(
            "replyFieldVariantStructRecursive")
        self.assertTrue(new_reply_field_variant_struct_recursive_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_REPLY_FIELD_NOT_SUBSET)
        self.assertRegex(
            str(new_reply_field_variant_struct_recursive_error), "replyFieldVariantStructRecursive")

        new_command_parameter_contains_validator_error = error_collection.get_error_by_command_name(
            "newCommandParameterValidator")
        self.assertTrue(new_command_parameter_contains_validator_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_CONTAINS_VALIDATOR)
        self.assertRegex(
            str(new_command_parameter_contains_validator_error), "newCommandParameterValidator")

        command_parameter_validators_not_equal_error = error_collection.get_error_by_command_name(
            "commandParameterValidatorsNotEqual")
        self.assertTrue(command_parameter_validators_not_equal_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_VALIDATORS_NOT_EQUAL)
        self.assertRegex(
            str(command_parameter_validators_not_equal_error), "commandParameterValidatorsNotEqual")

        new_command_type_contains_validator_error = error_collection.get_error_by_command_name(
            "newCommandTypeValidator")
        self.assertTrue(new_command_type_contains_validator_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_TYPE_CONTAINS_VALIDATOR)
        self.assertRegex(str(new_command_type_contains_validator_error), "newCommandTypeValidator")

        command_type_validators_not_equal_error = error_collection.get_error_by_command_name(
            "commandTypeValidatorsNotEqual")
        self.assertTrue(command_type_validators_not_equal_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_TYPE_VALIDATORS_NOT_EQUAL)
        self.assertRegex(
            str(command_type_validators_not_equal_error), "commandTypeValidatorsNotEqual")

        new_param_variant_not_superset_error = error_collection.get_error_by_command_name(
            "newParamVariantNotSuperset")
        self.assertTrue(new_param_variant_not_superset_error.error_id == idl_compatibility_errors.
                        ERROR_ID_NEW_COMMAND_PARAMETER_VARIANT_TYPE_NOT_SUPERSET)
        self.assertRegex(str(new_param_variant_not_superset_error), "newParamVariantNotSuperset")

        new_param_variant_not_superset_two_errors = error_collection.get_all_errors_by_command_name(
            "newParamVariantNotSupersetTwo")
        self.assertTrue(len(new_param_variant_not_superset_two_errors) == 2)
        for error in new_param_variant_not_superset_two_errors:
            self.assertTrue(error.error_id == idl_compatibility_errors.
                            ERROR_ID_NEW_COMMAND_PARAMETER_VARIANT_TYPE_NOT_SUPERSET)

        new_param_type_not_variant_error = error_collection.get_error_by_command_name(
            "newParamTypeNotVariant")
        self.assertTrue(new_param_type_not_variant_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_COMMAND_PARAMETER_TYPE_NOT_VARIANT)
        self.assertRegex(str(new_param_type_not_variant_error), "newParamTypeNotVariant")

        new_param_variant_recursive_error = error_collection.get_error_by_command_name(
            "newParamVariantRecursive")
        self.assertTrue(new_param_variant_recursive_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_TYPE_NOT_SUPERSET)
        self.assertRegex(str(new_param_variant_recursive_error), "newParamVariantRecursive")

        new_param_variant_struct_not_superset_error = error_collection.get_error_by_command_name(
            "newParamVariantStructNotSuperset")
        self.assertTrue(
            new_param_variant_struct_not_superset_error.error_id ==
            idl_compatibility_errors.ERROR_ID_NEW_COMMAND_PARAMETER_VARIANT_TYPE_NOT_SUPERSET)
        self.assertRegex(
            str(new_param_variant_struct_not_superset_error), "newParamVariantStructNotSuperset")

        new_param_variant_struct_recursive_error = error_collection.get_error_by_command_name(
            "newParamVariantStructRecursive")
        self.assertTrue(new_param_variant_struct_recursive_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_PARAMETER_TYPE_NOT_SUPERSET)
        self.assertRegex(
            str(new_param_variant_struct_recursive_error), "newParamVariantStructRecursive")

        new_command_type_variant_not_superset_error = error_collection.get_error_by_command_name(
            "newCommandTypeVariantNotSuperset")
        self.assertTrue(new_command_type_variant_not_superset_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_COMMAND_VARIANT_TYPE_NOT_SUPERSET)
        self.assertRegex(
            str(new_command_type_variant_not_superset_error), "newCommandTypeVariantNotSuperset")

        new_command_type_variant_not_superset_two_errors = error_collection.get_all_errors_by_command_name(
            "newCommandTypeVariantNotSupersetTwo")
        self.assertTrue(len(new_command_type_variant_not_superset_two_errors) == 2)
        for error in new_command_type_variant_not_superset_two_errors:
            self.assertTrue(error.error_id ==
                            idl_compatibility_errors.ERROR_ID_NEW_COMMAND_VARIANT_TYPE_NOT_SUPERSET)

        new_command_type_not_variant_error = error_collection.get_error_by_command_name(
            "newCommandTypeNotVariant")
        self.assertTrue(new_command_type_not_variant_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_COMMAND_TYPE_NOT_VARIANT)
        self.assertRegex(str(new_command_type_not_variant_error), "newCommandTypeNotVariant")

        new_command_type_variant_recursive_error = error_collection.get_error_by_command_name(
            "newCommandTypeVariantRecursive")
        self.assertTrue(new_command_type_variant_recursive_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_TYPE_NOT_SUPERSET)
        self.assertRegex(
            str(new_command_type_variant_recursive_error), "newCommandTypeVariantRecursive")

        new_command_type_variant_struct_not_superset_error = error_collection.get_error_by_command_name(
            "newCommandTypeVariantStructNotSuperset")
        self.assertTrue(new_command_type_variant_struct_not_superset_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_COMMAND_VARIANT_TYPE_NOT_SUPERSET)
        self.assertRegex(
            str(new_command_type_variant_struct_not_superset_error),
            "newCommandTypeVariantStructNotSuperset")

        new_command_type_variant_struct_recursive_error = error_collection.get_error_by_command_name(
            "newCommandTypeVariantStructRecursive")
        self.assertTrue(new_command_type_variant_struct_recursive_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_COMMAND_TYPE_NOT_SUPERSET)
        self.assertRegex(
            str(new_command_type_variant_struct_recursive_error),
            "newCommandTypeVariantStructRecursive")
        new_reply_field_contains_validator_error = error_collection.get_error_by_command_name(
            "newReplyFieldValidator")
        self.assertTrue(new_reply_field_contains_validator_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_REPLY_FIELD_CONTAINS_VALIDATOR)
        self.assertRegex(str(new_reply_field_contains_validator_error), "newReplyFieldValidator")

        reply_field_validators_not_equal_error = error_collection.get_error_by_command_name(
            "replyFieldValidatorsNotEqual")
        self.assertTrue(reply_field_validators_not_equal_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_REPLY_FIELD_VALIDATORS_NOT_EQUAL)
        self.assertRegex(
            str(reply_field_validators_not_equal_error), "replyFieldValidatorsNotEqual")

        simple_check_not_equal_error = error_collection.get_error_by_command_name(
            "simpleCheckNotEqual")
        self.assertTrue(simple_check_not_equal_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_CHECK_NOT_EQUAL)
        self.assertRegex(str(simple_check_not_equal_error), "simpleCheckNotEqual")

        simple_check_not_equal_error_two = error_collection.get_error_by_command_name(
            "simpleCheckNotEqualTwo")
        self.assertTrue(simple_check_not_equal_error_two.error_id ==
                        idl_compatibility_errors.ERROR_ID_CHECK_NOT_EQUAL)
        self.assertRegex(str(simple_check_not_equal_error_two), "simpleCheckNotEqualTwo")

        simple_check_not_equal_error_three = error_collection.get_error_by_command_name(
            "simpleCheckNotEqualThree")
        self.assertTrue(simple_check_not_equal_error_three.error_id ==
                        idl_compatibility_errors.ERROR_ID_CHECK_NOT_EQUAL)
        self.assertRegex(str(simple_check_not_equal_error_three), "simpleCheckNotEqualThree")

        simple_resource_pattern_not_equal_error = error_collection.get_error_by_command_name(
            "simpleResourcePatternNotEqual")
        self.assertTrue(simple_resource_pattern_not_equal_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_RESOURCE_PATTERN_NOT_EQUAL)
        self.assertRegex(
            str(simple_resource_pattern_not_equal_error), "simpleResourcePatternNotEqual")

        new_simple_action_types_not_subset_error = error_collection.get_error_by_command_name(
            "newSimpleActionTypesNotSubset")
        self.assertTrue(new_simple_action_types_not_subset_error.error_id ==
                        idl_compatibility_errors.ERROR_ID_NEW_ACTION_TYPES_NOT_SUBSET)
        self.assertRegex(
            str(new_simple_action_types_not_subset_error), "newSimpleActionTypesNotSubset")

    def test_error_reply(self):
        """Tests the compatibility checker with the ErrorReply struct."""
        dir_path = path.dirname(path.realpath(__file__))

        self.assertFalse(
            idl_check_compatibility.check_error_reply(
                path.join(dir_path, "compatibility_test_pass/old/error_reply.idl"),
                path.join(dir_path, "compatibility_test_pass/new/error_reply.idl"),
                []).has_errors())

        error_collection_fail = idl_check_compatibility.check_error_reply(
            path.join(dir_path, "compatibility_test_fail/old/error_reply.idl"),
            path.join(dir_path, "compatibility_test_fail/new/error_reply.idl"), [])

        self.assertTrue(error_collection_fail.has_errors())
        self.assertTrue(error_collection_fail.count() == 1)

        new_error_reply_field_optional_error = error_collection_fail.get_error_by_error_id(
            idl_compatibility_errors.ERROR_ID_NEW_REPLY_FIELD_OPTIONAL)
        self.assertRegex(str(new_error_reply_field_optional_error), "n/a")


if __name__ == '__main__':
    unittest.main()
