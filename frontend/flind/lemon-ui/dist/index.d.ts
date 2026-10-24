import React$1, { MouseEventHandler, ReactNode, HTMLProps } from 'react';
import { Placement } from '@popperjs/core';
import { ModalProps } from 'antd';
import { ToastOptions } from 'react-toastify';

interface LemonBubbleProps {
    count?: number;
    size?: 'small' | 'medium' | 'large';
    position?: 'none' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
    showZero?: boolean;
}
/** An icon-sized Bubble for displaying a count.
 *
 *  Numbers up to 9 are displayed in full, in integer form, with 9+ for higher values
 */
declare function LemonBubble({ count, size, position, showZero, }: LemonBubbleProps): JSX.Element;

declare module 'react' {
    function forwardRef<T, P>(render: (props: P, ref: React$1.Ref<T>) => React$1.ReactElement | null): (props: P & React$1.RefAttributes<T>) => React$1.ReactElement | null;
}
interface LemonRowPropsBase<T extends keyof JSX.IntrinsicElements> extends Omit<React$1.HTMLProps<JSX.IntrinsicElements[T]>, 'ref' | 'size'> {
    /** If icon width is relaxed, width of icon box is set to auto. Default icon width is 1em  */
    relaxedIconWidth?: boolean;
    icon?: React$1.ReactElement | null;
    /** HTML tag to render the row with. */
    tag?: T;
    status?: 'success' | 'warning' | 'danger' | 'highlighted' | 'muted';
    /** Extended content, e.g. a description, to show in the lower button area. */
    extendedContent?: React$1.ReactNode;
    loading?: boolean;
    /** Tooltip to display on hover. */
    tooltip?: any;
    /** Whether the row should take up the parent's full width. */
    fullWidth?: boolean;
    /** Whether the row's contents should be centered. */
    center?: boolean;
    /** Whether the element should be outlined with a standard border. */
    outlined?: any;
    /** Variation on sizes - default is medium. Small looks better inline with text. Large is a chunkier row.  */
    size?: 'small' | 'medium' | 'large';
    'data-attr'?: string;
}
interface LemonRowProps<T extends keyof JSX.IntrinsicElements = 'div'> extends LemonRowPropsBase<T> {
    sideIcon?: React$1.ReactElement | false | null;
}
/** Generic UI row component. Can be exploited as a button (see LemonButton) or just as a standard row of content.
 *
 * Do NOT use for general layout if you simply need flexbox though. In that case `display: flex` is much lighter.
 */
declare const LemonRow: <T extends keyof JSX.IntrinsicElements = "div">(props: LemonRowProps<T> & React$1.RefAttributes<HTMLElement>) => React$1.ReactElement<any, string | React$1.JSXElementConstructor<any>> | null;

interface PopupProps {
    visible?: boolean;
    onClickOutside?: (event: Event) => void;
    onClickInside?: MouseEventHandler<HTMLDivElement>;
    /** Popover trigger element. */
    children: React$1.ReactChild | ((props: {
        setRef: (ref: HTMLElement | null) => void;
    }) => JSX.Element);
    /** Content of the overlay. */
    overlay: React$1.ReactNode | React$1.ReactNode[];
    /** Where the popover should start relative to children. */
    placement?: Placement;
    /** Where the popover should start relative to children if there's insufficient space for original placement. */
    fallbackPlacements?: Placement[];
    /** Whether the popover is actionable rather than just informative - actionable means a colored border. */
    actionable?: boolean;
    /** Whether the popover's width should be synced with the children's width. */
    sameWidth?: boolean;
    className?: string;
    modifier?: Record<string, any>;
}

interface LemonButtonPopup extends Omit<PopupProps, 'children'> {
    closeOnClickInside?: boolean;
}
interface LemonButtonPropsBase extends Omit<LemonRowPropsBase<'button'>, 'tag' | 'type' | 'ref'> {
    ref?: React$1.Ref<HTMLButtonElement>;
    type?: 'default' | 'alt' | 'primary' | 'secondary' | 'tertiary' | 'stealth' | 'highlighted';
    htmlType?: LemonRowPropsBase<'button'>['type'];
    /** Whether the button should have transparent background in its base state (i.e. non-hover). */
    translucent?: boolean;
    /** Whether hover style should be applied, signaling that the button is held active in some way. */
    active?: boolean;
    /** URL to link to. */
    to?: string;
}
interface LemonButtonProps extends LemonButtonPropsBase {
    sideIcon?: React$1.ReactElement | null;
    /** DEPRECATED: Use `LemonButtonWithPopup` instead. */
    popup?: LemonButtonPopup;
}
declare const LemonButton: (props: LemonButtonProps & React$1.RefAttributes<HTMLButtonElement>) => React$1.ReactElement<any, string | React$1.JSXElementConstructor<any>> | null;
declare type SideAction = Pick<LemonButtonProps, 'onClick' | 'popup' | 'to' | 'disabled' | 'icon' | 'type' | 'tooltip' | 'data-attr'>;
/** A LemonButtonWithSideAction can't have a sideIcon - instead it has a clickable sideAction. */
interface LemonButtonWithSideActionProps extends LemonButtonPropsBase {
    sideAction: SideAction;
}
/**
 * Styled button with a side action on the right.
 * We can't use `LemonRow`'s `sideIcon` prop because putting `onClick` on it clashes with the parent`s `onClick`.
 */
declare function LemonButtonWithSideAction({ sideAction, children, ...buttonProps }: LemonButtonWithSideActionProps): JSX.Element;
interface LemonButtonWithPopupProps extends LemonButtonPropsBase {
    popup: LemonButtonPopup;
    sideIcon?: React$1.ReactElement | null;
}
/**
 * Styled button that opens a popup menu on click.
 * The difference vs. plain `LemonButton` is popup visibility being controlled internally, which is more convenient.
 */
declare function LemonButtonWithPopup({ popup: { onClickOutside, onClickInside, closeOnClickInside, ...popupProps }, onClick, ...buttonProps }: LemonButtonWithPopupProps): JSX.Element;

interface LemonCheckboxProps {
    checked?: boolean | 'indeterminate';
    defaultChecked?: boolean;
    disabled?: boolean;
    onChange?: (event: React$1.ChangeEvent<HTMLInputElement>) => void;
    label?: string | JSX.Element;
    id?: string;
    className?: string;
    style?: React$1.CSSProperties;
    /** @deprecated See https://github.com/PostHog/posthog/pull/9357#pullrequestreview-933783868. */
    color?: string;
    rowProps?: LemonRowProps<'div'>;
}
interface BoxCSSProperties extends React$1.CSSProperties {
    '--box-color': string;
}
/** `LemonRow`-based checkbox component for use in lists or forms.
 *
 * As opposed to switches, checkboxes don't always have to result in the change being applied immediately.
 * E.g. the change may only be applied when the user clicks "Save" in a form.
 */
declare function LemonCheckbox({ checked, defaultChecked, disabled, onChange, label, id: rawId, className, color, rowProps, style, }: LemonCheckboxProps): JSX.Element;

interface LemonDividerProps {
    /** Twice the default amount of margin. */
    large?: boolean;
    /** 3x the thickness of the line. */
    thick?: boolean;
    /** Whether the divider should be vertical (for separating left-to-right) instead of horizontal (top-to-bottom). */
    vertical?: boolean;
    /** Whether the divider should be a dashed line. */
    dashed?: boolean;
    style?: React$1.CSSProperties;
}
/** A separator, ideal for being sandwiched between `LemonRow`s.
 *
 * Horizontal by default but can be used in vertical form too.
 */
declare function LemonDivider({ large, vertical, dashed, thick, style, }: LemonDividerProps): JSX.Element;

interface LemonInputProps extends Omit<React$1.InputHTMLAttributes<HTMLInputElement>, 'value' | 'defaultValue' | 'onChange' | 'prefix' | 'suffix'> {
    ref?: React$1.Ref<HTMLInputElement>;
    id?: string;
    value?: string | number;
    defaultValue?: string;
    placeholder?: string;
    onChange?: (newValue: string) => void;
    onPressEnter?: (newValue: string) => void;
    /** An embedded input has no border around it and no background. This way it blends better into other components. */
    embedded?: boolean;
    /** Whether there should be a clear icon to the right allowing you to reset the input. The `suffix` prop will be ignored if clearing is allowed. */
    allowClear?: boolean;
    /** Icon to prefix input field */
    icon?: React$1.ReactElement | null;
    /** Icon to suffix input field */
    sideIcon?: React$1.ReactElement | null;
    /** Whether input field is disabled */
    disabled?: boolean;
}
/** A `LemonRow`-based `input` component for single-line text. */
declare const LemonInput: (props: LemonInputProps & React$1.RefAttributes<HTMLInputElement>) => React$1.ReactElement<any, string | React$1.JSXElementConstructor<any>> | null;

declare type LemonModalProps = React$1.PropsWithChildren<Omit<ModalProps, 'closeIcon'>>;
/** A lightweight wrapper over Ant's Modal for matching Lemon style. */
declare function LemonModal({ className, footer, width, ...modalProps }: LemonModalProps): JSX.Element;

interface LemonSelectOption {
    label: string;
    icon?: React$1.ReactElement;
    disabled?: boolean;
    'data-attr'?: string;
}
declare type LemonSelectOptions = Record<string | number, LemonSelectOption>;
interface LemonSelectProps<O extends LemonSelectOptions> extends Omit<LemonButtonWithPopupProps, 'popup' | 'icon' | 'value' | 'defaultValue' | 'onChange'> {
    options: O;
    value?: keyof O | null;
    onChange?: (newValue: keyof O | null) => void;
    dropdownMatchSelectWidth?: boolean;
    allowClear?: boolean;
}
declare function LemonSelect<O extends LemonSelectOptions>({ value, onChange, options, placeholder, dropdownMatchSelectWidth, allowClear, ...buttonProps }: LemonSelectProps<O>): JSX.Element;

interface LemonSwitchProps extends Omit<LemonRowProps<'div'>, 'alt' | 'label' | 'onChange' | 'outlined'> {
    onChange: (newChecked: boolean) => void;
    checked: boolean;
    label?: string | JSX.Element;
    /** Whether the switch should use the alternative primary color. */
    alt?: boolean;
    /** Default switches are inline. Primary switches _with a label_ are wrapped in an outlined block. */
    type?: 'default' | 'primary';
}
/** `LemonRow`-based switch component for boolean settings where the change is immediately applied.
 *
 * If part of a form, use `LemonCheckbox` instead.
 */
declare function LemonSwitch({ id: rawId, onChange, checked, disabled, loading, label, alt, type, className, 'data-attr': dataAttr, ...rowProps }: LemonSwitchProps): JSX.Element;

/** Sorting state. */
interface Sorting {
    columnKey: string;
    /** 1 means ascending, -1 means descending. */
    order: 1 | -1;
}

interface TableCellRepresentation {
    children?: any;
    props?: HTMLProps<HTMLTableCellElement>;
}
declare type TableCellRenderResult = TableCellRepresentation | ReactNode | JSX.Element | string | number | false | null | undefined;
interface LemonTableColumn<T extends Record<string, any>, D extends keyof T | undefined> {
    title?: string | React.ReactNode;
    key?: string;
    dataIndex?: D;
    render?: (dataValue: D extends keyof T ? T[D] : undefined, record: T, recordIndex: number) => TableCellRenderResult;
    /** Sorting function. Set to `true` if using manual pagination, in which case you'll also have to provide `sorting` on the table. */
    sorter?: ((a: T, b: T) => number) | true;
    className?: string;
    /** Column content alignment. Left by default. Set to right for numerical values (amounts, days ago etc.) */
    align?: 'left' | 'right' | 'center';
    /** TODO: Whether the column should be sticky when scrolling */
    sticky?: boolean;
    /** Set width. */
    width?: string | number;
}
interface LemonTableColumnGroup<T extends Record<string, any>> {
    title?: string | React.ReactNode;
    children: LemonTableColumn<T, keyof T | undefined>[];
}
declare type LemonTableColumns<T extends Record<string, any>> = LemonTableColumn<T, keyof T | undefined>[] | LemonTableColumnGroup<T>[];
interface ExpandableConfig<T extends Record<string, any>> {
    /** Row expansion render function. */
    expandedRowRender: (record: T, recordIndex: number) => any;
    /**
     * Function determining whether the row should be expandable:
     * A positive value (like true or 1) means that the row is expandable.
     * A zero (like 0 or false) means that the row isn't expandable.
     * A negative value (like -1) means that the row isn't expandable and that also the expand button cell is skipped.
     */
    rowExpandable?: (record: T) => boolean | number;
    /** Called when row is expanded */
    onRowExpand?: (record: T) => void;
    /** Called when row is collapsed */
    onRowCollapse?: (record: T) => void;
    /** Disable indentation */
    noIndent?: boolean;
    /**
     * Callback that checks if a row expandable state should be overridden
     * A positive value (like true or 1) means that the row is expanded.
     * A zero (like 0 or false) means that the row is collapsed.
     * A negative value (like -1) means that the row is uncontrolled.
     */
    isRowExpanded?: (record: T) => boolean | number;
}

interface PaginationBase {
    /** By default pagination is only shown when there are multiple pages, but will always be if this is `false`. */
    hideOnSinglePage?: boolean;
}
interface PaginationAuto extends PaginationBase {
    controlled?: false;
    /** Size of each page (except the last one which can be smaller). */
    pageSize: number;
}
interface PaginationManual extends PaginationBase {
    controlled: true;
    /** Size of each page (except the last one which can be smaller)/ */
    pageSize?: number;
    /** Page currently on display. */
    currentPage?: number;
    /** Total entry count for determining current position using `currentPage`. If not set, position is not shown. */
    entryCount?: number;
    /** Next page navigation handler. */
    onForward?: () => void;
    /** Previous page navigation handler. */
    onBackward?: () => void;
}

interface LemonTableProps<T extends Record<string, any>> {
    /** Table ID that will also be used in pagination to add uniqueness to search params (page + order). */
    id?: string;
    columns: LemonTableColumns<T>;
    dataSource: T[];
    /** Which column to use for the row key, as an alternative to the default row index mechanism. */
    rowKey?: keyof T | ((record: T) => string | number);
    /** Class to append to each row. */
    rowClassName?: string | ((record: T) => string | null);
    /** Color to mark each row with. */
    rowRibbonColor?: string | ((record: T) => string | null);
    /** Status of each row. Defaults no status. */
    rowStatus?: 'highlighted' | ((record: T) => 'highlighted' | null);
    /** Function that for each row determines what props should its `tr` element have based on the row's record. */
    onRow?: (record: T) => Omit<HTMLProps<HTMLTableRowElement>, 'key'>;
    /** How tall should rows be. The default value is `"middle"`. */
    size?: 'small' | 'middle';
    /** An embedded table has no border around it and no background. This way it blends better into other components. */
    embedded?: boolean;
    loading?: boolean;
    pagination?: PaginationAuto | PaginationManual;
    expandable?: ExpandableConfig<T>;
    /** Whether the header should be shown. The default value is `true`. */
    showHeader?: boolean;
    /** Whether header titles should be uppercased. The default value is `true`. */
    uppercaseHeader?: boolean;
    /**
     * By default sorting goes: 0. unsorted > 1. ascending > 2. descending > GOTO 0 (loop).
     * With sorting cancellation disabled, GOTO 0 is replaced by GOTO 1. */
    disableSortingCancellation?: boolean;
    /** Sorting order to start with. */
    defaultSorting?: Sorting | null;
    /** Controlled sort order. */
    sorting?: Sorting | null;
    /** Sorting change handler for controlled sort order. */
    onSort?: (newSorting: Sorting | null) => void;
    /** How many skeleton rows should be used for the empty loading state. The default value is 1. */
    loadingSkeletonRows?: number;
    /** What to show when there's no data. */
    emptyState?: React$1.ReactNode;
    /** What to describe the entries as, singular and plural. The default value is `['entry', 'entries']`. */
    nouns?: [string, string];
    className?: string;
    style?: React$1.CSSProperties;
    'data-attr'?: string;
}
declare function LemonTable<T extends Record<string, any>>({ id, columns: rawColumns, dataSource, rowKey, rowClassName, rowRibbonColor, rowStatus, onRow, size, embedded, loading, pagination, expandable, showHeader, uppercaseHeader, disableSortingCancellation, defaultSorting, sorting, onSort, loadingSkeletonRows, emptyState, nouns, className, style, 'data-attr': dataAttr, }: LemonTableProps<T>): JSX.Element;

declare type LemonTagPropsType = 'warning' | 'danger' | 'success' | 'default';
interface LemonTagProps extends React$1.HTMLAttributes<HTMLDivElement> {
    type?: LemonTagPropsType;
    children: JSX.Element | string;
    icon?: JSX.Element;
}
declare function LemonTag({ type, children, className, icon, ...props }: LemonTagProps): JSX.Element;

interface LemonTextAreaProps extends Omit<React$1.TextareaHTMLAttributes<HTMLTextAreaElement>, 'value' | 'defaultValue' | 'onChange' | 'prefix' | 'suffix'> {
    ref?: React$1.Ref<HTMLTextAreaElement>;
    id?: string;
    value?: string;
    defaultValue?: string;
    placeholder?: string;
    onChange?: (newValue: string) => void;
    onPressEnter?: (newValue: string) => void;
    /** An embedded input has no border around it and no background. This way it blends better into other components. */
    embedded?: boolean;
    /** Whether there should be a clear icon to the right allowing you to reset the input. The `suffix` prop will be ignored if clearing is allowed. */
    allowClear?: boolean;
    /** Icon to prefix input field */
    icon?: React$1.ReactElement | null;
    /** Icon to suffix input field */
    sideIcon?: React$1.ReactElement | null;
    /** Whether input field is disabled */
    disabled?: boolean;
}
/** A `LemonRow`-based `textarea` component for multi-line text. */
declare const LemonTextArea: (props: LemonTextAreaProps & React$1.RefAttributes<HTMLTextAreaElement>) => React$1.ReactElement<any, string | React$1.JSXElementConstructor<any>> | null;

declare function ToastCloseButton({ closeToast }: {
    closeToast?: () => void;
}): JSX.Element;
interface ToastButton {
    label: string;
    action: () => void;
}
interface ToastOptionsWithButton extends ToastOptions {
    button?: ToastButton;
}
declare const GET_HELP_BUTTON: ToastButton;
interface ToastContentProps {
    type: 'info' | 'success' | 'warning' | 'error';
    message: string | JSX.Element;
    button?: ToastButton;
    id?: number | string;
}
declare function ToastContent({ type, message, button, id }: ToastContentProps): JSX.Element;
declare const lemonToast: {
    info(message: string | JSX.Element, { button, ...toastOptions }?: ToastOptionsWithButton): void;
    success(message: string | JSX.Element, { button, ...toastOptions }?: ToastOptionsWithButton): void;
    warning(message: string | JSX.Element, { button, ...toastOptions }?: ToastOptionsWithButton): void;
    error(message: string | JSX.Element, { button, ...toastOptions }?: ToastOptionsWithButton): void;
    dismiss(id?: string | number | undefined): void;
};

declare type RoutePart = string | Record<string, any>;
interface LinkProps extends React$1.HTMLProps<HTMLAnchorElement> {
    to?: string | [string, RoutePart?, RoutePart?];
    preventClick?: boolean;
    tag?: string | React$1.FunctionComponentElement<any>;
}
declare function Link({ to, preventClick, tag, ...props }: LinkProps): JSX.Element;

export { BoxCSSProperties, GET_HELP_BUTTON, LemonBubble, LemonBubbleProps, LemonButton, LemonButtonPopup, LemonButtonProps, LemonButtonPropsBase, LemonButtonWithPopup, LemonButtonWithPopupProps, LemonButtonWithSideAction, LemonButtonWithSideActionProps, LemonCheckbox, LemonCheckboxProps, LemonDivider, LemonDividerProps, LemonInput, LemonInputProps, LemonModal, LemonModalProps, LemonRow, LemonRowProps, LemonRowPropsBase, LemonSelect, LemonSelectOption, LemonSelectOptions, LemonSelectProps, LemonSwitch, LemonSwitchProps, LemonTable, LemonTableProps, LemonTag, LemonTagPropsType, LemonTextArea, LemonTextAreaProps, Link, LinkProps, SideAction, ToastCloseButton, ToastContent, ToastContentProps, lemonToast };
