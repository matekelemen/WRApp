/// @author Máté Kelemen

// --- WRApp Includes ---
#include "wrapp/io/inc/AddIOToPython.hpp"
#include "wrapp/io/inc/Journal.hpp"


namespace Kratos::Python {


void AddIOToPython(pybind11::module& rModule) {
    pybind11::class_<JournalBase, JournalBase::Pointer>(rModule, "JournalBase")
        .def(pybind11::init<const std::filesystem::path&>())
        .def(pybind11::init<const std::filesystem::path&,const JournalBase::Extractor&>())
        .def("GetFilePath",
             &JournalBase::GetFilePath,
             "Get the path to the underlying file.")
        .def("SetExtractor",
             pybind11::overload_cast<const JournalBase::Extractor&>(&JournalBase::SetExtractor),
             "Set the extractor handling the conversion from Model to string.")
        .def("Push",
             pybind11::overload_cast<const Model&>(&JournalBase::Push),
             "Insert a new entry at the end, extracted from the input model.")
        .def("EraseIf",
             &JournalBase::EraseIf,
             "Erase all lines from the associated file matching the provided predicate.")
        .def("Clear",
             &JournalBase::Clear,
             "Delete the registry file")
        .def("__len__",
             &JournalBase::size)
        .def("__iter__",
             [](const JournalBase& rJournal){return pybind11::make_iterator(rJournal.begin(), rJournal.end());})
        ;

    pybind11::class_<Journal, Journal::Pointer>(rModule, "Journal")
        .def(pybind11::init<const std::filesystem::path&>())
        .def(pybind11::init<const std::filesystem::path&,const Journal::Extractor&>())
        .def("GetFilePath",
             &Journal::GetFilePath,
             "Get the path to the underlying file.")
        .def("SetExtractor",
             pybind11::overload_cast<const Journal::Extractor&>(&Journal::SetExtractor),
             "Set the extractor handling the conversion from Model to Parameters")
        .def("Push",
             &Journal::Push,
             "Insert a new entry at the end, extracted from the input model.")
        .def("EraseIf",
             &Journal::EraseIf,
             "Erase all lines from the associated file matching the provided predicate.")
        .def("Clear",
             &Journal::Clear,
             "Delete the registry file")
        .def("__len__",
             &Journal::size)
        .def("__iter__",
             [](const Journal& rJournal){return pybind11::make_iterator(rJournal.begin(), rJournal.end());})
        ;
}


} // namespace Kratos::Python
