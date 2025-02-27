import {
    LemonButton,
    LemonInput,
    LemonInputSelect,
    LemonModal,
    LemonSegmentedButton,
    LemonSelect,
} from '@posthog/lemon-ui'
import { useActions, useValues } from 'kea'
import { LemonField } from 'lib/lemon-ui/LemonField'

import { Variable, VariableType } from '../../types'
import { VariableCalendar } from './VariableCalendar'
import { variableModalLogic } from './variableModalLogic'

const renderVariableSpecificFields = (
    variable: Variable,
    updateVariable: (variable: Variable) => void,
    onSave: () => void
): JSX.Element => {
    if (variable.type === 'String') {
        return (
            <LemonField.Pure label="Default value" className="gap-1">
                <LemonInput
                    placeholder="Default value"
                    value={variable.default_value}
                    onChange={(value) => updateVariable({ ...variable, default_value: value })}
                />
            </LemonField.Pure>
        )
    }

    if (variable.type === 'Number') {
        return (
            <LemonField.Pure label="Default value" className="gap-1">
                <LemonInput
                    placeholder="Default value"
                    type="number"
                    value={variable.default_value}
                    onChange={(value) => updateVariable({ ...variable, default_value: value ?? 0 })}
                />
            </LemonField.Pure>
        )
    }

    if (variable.type === 'Boolean') {
        return (
            <LemonField.Pure label="Default value" className="gap-1">
                <LemonSegmentedButton
                    className="w-full"
                    value={variable.default_value ? 'true' : 'false'}
                    onChange={(value) => updateVariable({ ...variable, default_value: value === 'true' })}
                    options={[
                        {
                            value: 'true',
                            label: 'true',
                        },
                        {
                            value: 'false',
                            label: 'false',
                        },
                    ]}
                />
            </LemonField.Pure>
        )
    }

    if (variable.type === 'List') {
        return (
            <>
                <LemonField.Pure label="Values" className="gap-1">
                    <LemonInputSelect
                        value={variable.values}
                        onChange={(value) => updateVariable({ ...variable, values: value })}
                        placeholder="Options..."
                        mode="multiple"
                        allowCustomValues={true}
                        options={[]}
                    />
                </LemonField.Pure>
                <LemonField.Pure label="Default value" className="gap-1">
                    <LemonSelect
                        className="w-full"
                        placeholder="Select default value"
                        value={variable.default_value}
                        options={variable.values.map((n) => ({ label: n, value: n }))}
                        onChange={(value) => updateVariable({ ...variable, default_value: value ?? '' })}
                        allowClear
                        dropdownMaxContentWidth
                    />
                </LemonField.Pure>
            </>
        )
    }

    if (variable.type === 'Date') {
        return (
            <LemonField.Pure label="Default value" className="gap-1">
                <VariableCalendar
                    showDefault={true}
                    variable={variable}
                    updateVariable={(date) => {
                        updateVariable({ ...variable, default_value: date })
                        // calendar is a special case to reuse LemonCalendarSelect
                        onSave()
                    }}
                />
            </LemonField.Pure>
        )
    }

    throw new Error(`Unsupported variable type: ${(variable as Variable).type}`)
}

export const NewVariableModal = (): JSX.Element => {
    const { closeModal, updateVariable, save, openNewVariableModal } = useActions(variableModalLogic)
    const { isModalOpen, variable, modalType } = useValues(variableModalLogic)

    const title = modalType === 'new' ? `New ${variable.type} variable` : `Editing ${variable.name}`

    return (
        <LemonModal
            title={title}
            isOpen={isModalOpen}
            onClose={closeModal}
            maxWidth="30rem"
            footer={
                variable.type !== 'Date' && (
                    <div className="flex flex-1 justify-end gap-2">
                        <LemonButton type="secondary" onClick={closeModal}>
                            Close
                        </LemonButton>
                        <LemonButton type="primary" onClick={() => save()}>
                            Save
                        </LemonButton>
                    </div>
                )
            }
        >
            <div className="gap-4 flex flex-col">
                <LemonField.Pure label="Name" className="gap-1">
                    <LemonInput
                        placeholder="Name"
                        value={variable.name}
                        onChange={(value) => updateVariable({ ...variable, name: value })}
                    />
                </LemonField.Pure>
                <LemonField.Pure label="Type" className="gap-1">
                    <LemonSelect
                        value={variable.type}
                        onChange={(value) => openNewVariableModal(value as VariableType)}
                        options={[
                            {
                                value: 'String',
                                label: 'String',
                            },
                            {
                                value: 'Number',
                                label: 'Number',
                            },
                            {
                                value: 'Boolean',
                                label: 'Boolean',
                            },
                            {
                                value: 'List',
                                label: 'List',
                            },
                            {
                                value: 'Date',
                                label: 'Date',
                            },
                        ]}
                    />
                </LemonField.Pure>
                {renderVariableSpecificFields(variable, updateVariable, save)}
            </div>
        </LemonModal>
    )
}
